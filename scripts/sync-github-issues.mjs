#!/usr/bin/env node

/**
 * Sync GitHub issues to local markdown documentation
 *
 * Features:
 * - Fetches all issues (open + closed) via gh CLI
 * - Downloads images to docs/issues/images/
 * - Rewrites image URLs to local paths
 * - Generates individual issue files (docs/issues/{number}.md)
 * - Generates master index (docs/issues/README.md)
 * - Preserves existing images (incremental updates)
 *
 * Usage: node scripts/sync-github-issues.mjs [--force-images]
 */

import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync, unlinkSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PROJECT_ROOT = join(__dirname, '..');

const ISSUES_DIR = join(PROJECT_ROOT, 'docs/issues');
const IMAGES_DIR = join(ISSUES_DIR, 'images');
const REPO = 'jt196/tradebacklinks';

// Ensure directories exist
[ISSUES_DIR, IMAGES_DIR].forEach(dir => {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
});

// Parse CLI args
const FORCE_IMAGES = process.argv.includes('--force-images');
const PUSH_STATE_FROM_LOCAL = process.argv.includes('--push-state');

/**
 * Fetch tracked issues (children) via GraphQL
 */
function fetchTrackedIssues(issueNumber) {
  try {
    const query = `{
      repository(owner: "jt196", name: "tradebacklinks") {
        issue(number: ${issueNumber}) {
          trackedIssues(first: 50) {
            nodes {
              number
              title
              state
            }
          }
        }
      }
    }`;

    const result = execSync(`gh api graphql -f query='${query}'`, { encoding: 'utf-8' });
    const data = JSON.parse(result);
    return data.data?.repository?.issue?.trackedIssues?.nodes || [];
  } catch (error) {
    console.warn(`  ⚠️  Failed to fetch tracked issues for #${issueNumber}:`, error.message);
    return [];
  }
}

/**
 * Fetch all issues from GitHub with relationship data
 */
function fetchIssues() {
  console.log('🔍 Fetching issues from GitHub...');

  const fields = [
    'number', 'title', 'body', 'state', 'labels',
    'assignees', 'milestone', 'createdAt', 'updatedAt',
    'closedAt', 'comments', 'author'
  ];

  const cmd = `gh issue list --repo ${REPO} --state all --limit 1000 --json ${fields.join(',')}`;

  try {
    const output = execSync(cmd, { encoding: 'utf-8' });
    const issues = JSON.parse(output);
    console.log(`✅ Found ${issues.length} issues`);

    // Fetch sub-issues summary via REST API for each issue
    console.log('🔗 Fetching issue relationships...');
    for (const issue of issues) {
      try {
        const apiData = execSync(`gh api /repos/${REPO}/issues/${issue.number}`, { encoding: 'utf-8' });
        const apiIssue = JSON.parse(apiData);
        issue.sub_issues_summary = apiIssue.sub_issues_summary || null;

        // Fetch tracked issues (children) via GraphQL
        if (issue.sub_issues_summary && issue.sub_issues_summary.total > 0) {
          issue.trackedIssues = fetchTrackedIssues(issue.number);
        } else {
          issue.trackedIssues = [];
        }
      } catch (error) {
        console.warn(`  ⚠️  Failed to fetch relationships for #${issue.number}`);
        issue.sub_issues_summary = null;
        issue.trackedIssues = [];
      }
    }

    return issues;
  } catch (error) {
    console.error('❌ Failed to fetch issues:', error.message);
    process.exit(1);
  }
}

/**
 * Download image from URL to local path with retry logic
 * Uses curl with gh auth token for private repo access
 */
async function downloadImage(url, localPath, retries = 3) {
  // Skip if exists and not forcing
  if (!FORCE_IMAGES && existsSync(localPath)) {
    console.log(`  ⏭️  Skipping existing: ${localPath}`);
    return localPath;
  }

  console.log(`  📥 Downloading: ${url}`);

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      // Get gh auth token and use with curl (-L follows redirects, -s silent mode)
      const curlCmd = `curl -L -s -H "Authorization: token $(gh auth token)" "${url}" -o "${localPath}"`;

      execSync(curlCmd, {
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: '/bin/bash'
      });

      // Check if file was actually downloaded and has content
      const stats = existsSync(localPath) ? statSync(localPath) : null;
      if (!stats || stats.size === 0) {
        throw new Error('Downloaded file is empty');
      }

      console.log(`  ✅ Saved: ${localPath} (${stats.size} bytes)`);
      return localPath;
    } catch (error) {
      // Clean up failed download
      try {
        if (existsSync(localPath)) {
          unlinkSync(localPath);
        }
      } catch (e) {
        // Ignore cleanup errors
      }

      if (attempt === retries) {
        console.warn(`  ⚠️  Failed after ${retries} attempts: ${error.message}`);
        throw error;
      }
      // Exponential backoff
      const delay = Math.pow(2, attempt) * 1000;
      console.log(`  🔄 Retry ${attempt}/${retries} after ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

/**
 * Extract and download images from markdown text
 * Returns updated text with rewritten URLs
 */
async function processImages(text, issueNumber) {
  if (!text) return '';

  // Match both markdown and HTML image syntax
  const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)|<img[^>]+src=["']([^"']+)["'][^>]*>/g;

  const images = [];
  let match;

  while ((match = imageRegex.exec(text)) !== null) {
    const url = match[2] || match[3]; // Markdown or HTML
    const alt = match[1] || 'Image';

    // Only process GitHub-hosted images
    if (url && (url.includes('github.com') || url.includes('githubusercontent.com'))) {
      images.push({ url, alt, fullMatch: match[0] });
    }
  }

  console.log(`  Found ${images.length} images in issue #${issueNumber}`);

  // Download images and rewrite URLs
  let updatedText = text;

  for (let i = 0; i < images.length; i++) {
    const { url, alt, fullMatch } = images[i];

    // Generate local filename
    // GitHub attachment URLs don't have extensions, default to png
    const urlParts = url.split('/');
    const lastPart = urlParts[urlParts.length - 1];
    const hasExtension = lastPart.includes('.') && lastPart.split('.').pop().length <= 4;
    const ext = hasExtension ? lastPart.split('.').pop().split('?')[0] : 'png';
    const localFilename = `issue-${issueNumber}-${i + 1}.${ext}`;
    const localPath = join(IMAGES_DIR, localFilename);
    const relativePath = `images/${localFilename}`;

    try {
      await downloadImage(url, localPath);

      // Rewrite URL in text (convert all to markdown format for consistency)
      updatedText = updatedText.replace(fullMatch, `![${alt}](${relativePath})`);
    } catch (error) {
      console.warn(`  ⚠️  Failed to download ${url}:`, error.message);
      // Keep original URL if download fails
    }
  }

  return updatedText;
}

/**
 * Generate individual issue markdown file
 */
async function generateIssueFile(issue) {
  console.log(`📝 Generating issue #${issue.number}: ${issue.title}`);

  // Process images in body
  const processedBody = await processImages(issue.body || '', issue.number);

  // Process images in comments
  const processedComments = [];
  for (const comment of issue.comments || []) {
    const processedComment = {
      ...comment,
      body: await processImages(comment.body, issue.number)
    };
    processedComments.push(processedComment);
  }

  // Generate front matter
  const frontMatter = {
    number: issue.number,
    title: issue.title,
    state: issue.state,
    labels: issue.labels.map(l => l.name),
    assignees: issue.assignees.map(a => a.login),
    milestone: issue.milestone?.title || null,
    created: issue.createdAt,
    updated: issue.updatedAt,
    closed: issue.closedAt,
    author: issue.author?.login || 'unknown',
    commentCount: processedComments.length,
    githubUrl: `https://github.com/${REPO}/issues/${issue.number}`
  };

  // Build markdown content
  let content = `---\n`;
  content += `# Issue #${issue.number}: ${issue.title}\n\n`;
  content += `**Status:** ${issue.state.toUpperCase()}\n`;
  content += `**Created:** ${new Date(issue.createdAt).toLocaleDateString()}\n`;
  content += `**Updated:** ${new Date(issue.updatedAt).toLocaleDateString()}\n`;

  if (issue.labels.length > 0) {
    content += `**Labels:** ${issue.labels.map(l => l.name).join(', ')}\n`;
  }

  if (issue.assignees.length > 0) {
    content += `**Assignees:** ${issue.assignees.map(a => a.login).join(', ')}\n`;
  }

  if (issue.milestone) {
    content += `**Milestone:** ${issue.milestone.title}\n`;
  }

  content += `**GitHub:** [View on GitHub](${frontMatter.githubUrl})\n\n`;
  content += `---\n\n`;

  // Add body
  content += `## Description\n\n`;
  content += processedBody || '_No description provided_\n\n';

  // Add sub-issues (children) if any
  if (issue.sub_issues_summary && issue.sub_issues_summary.total > 0) {
    content += `## Sub-Issues\n\n`;
    content += `**Progress:** ${issue.sub_issues_summary.completed}/${issue.sub_issues_summary.total} (${issue.sub_issues_summary.percent_completed}%)\n\n`;

    if (issue.trackedIssues && issue.trackedIssues.length > 0) {
      for (const subIssue of issue.trackedIssues) {
        const stateIcon = subIssue.state === 'OPEN' ? '🟢' : '⚪';
        content += `- ${stateIcon} [#${subIssue.number}](${subIssue.number}.md): ${subIssue.title}\n`;
      }
    }
    content += '\n';
  }

  // Add comments
  if (processedComments.length > 0) {
    content += `## Comments (${processedComments.length})\n\n`;

    for (const comment of processedComments) {
      const commentDate = new Date(comment.createdAt).toLocaleDateString();
      content += `### ${comment.author.login} - ${commentDate}\n\n`;
      content += comment.body + '\n\n';
      content += `---\n\n`;
    }
  }

  // Add metadata footer with relationships
  frontMatter.subIssues = issue.sub_issues_summary || null;
  frontMatter.trackedIssues = issue.trackedIssues?.map(si => ({ number: si.number, title: si.title, state: si.state })) || [];

  content += `<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->\n`;
  content += `<!-- Last synced: ${new Date().toISOString()} -->\n`;
  content += `<!-- Metadata: ${JSON.stringify(frontMatter, null, 2)} -->\n`;

  // Write file
  const filePath = join(ISSUES_DIR, `${issue.number}.md`);
  writeFileSync(filePath, content, 'utf-8');
  console.log(`✅ Saved: ${filePath}`);
}

/**
 * Generate master README.md index
 */
function generateIndex(issues) {
  console.log('📋 Generating master index...');

  let content = `# GitHub Issues - TradeBacklinks Migration\n\n`;
  content += `**AUTO-GENERATED DOCUMENTATION** - Do not edit manually\n\n`;
  content += `Last synced: ${new Date().toISOString()}\n\n`;
  content += `Total issues: ${issues.length}\n\n`;

  // Statistics
  const openIssues = issues.filter(i => i.state === 'OPEN');
  const closedIssues = issues.filter(i => i.state === 'CLOSED');

  content += `## Quick Stats\n\n`;
  content += `- **Open:** ${openIssues.length}\n`;
  content += `- **Closed:** ${closedIssues.length}\n`;
  content += `- **Total:** ${issues.length}\n\n`;

  // All labels
  const allLabels = new Set();
  issues.forEach(i => i.labels.forEach(l => allLabels.add(l.name)));
  if (allLabels.size > 0) {
    content += `**Labels:** ${Array.from(allLabels).join(', ')}\n\n`;
  }

  // Table of issues
  content += `## All Issues\n\n`;
  content += `| # | Title | State | Labels | Assignees | Comments | Updated |\n`;
  content += `|---|-------|-------|--------|-----------|----------|----------|\n`;

  // Sort by number descending (newest first)
  const sortedIssues = [...issues].sort((a, b) => b.number - a.number);

  for (const issue of sortedIssues) {
    const labels = issue.labels.map(l => l.name).join(', ') || '-';
    const assignees = issue.assignees.map(a => a.login).join(', ') || '-';
    const updated = new Date(issue.updatedAt).toLocaleDateString();
    const stateEmoji = issue.state === 'OPEN' ? '🟢' : '⚪';

    content += `| [${issue.number}](${issue.number}.md) | ${issue.title} | ${stateEmoji} ${issue.state} | ${labels} | ${assignees} | ${issue.comments?.length || 0} | ${updated} |\n`;
  }

  content += `\n---\n\n`;

  // Open issues section
  if (openIssues.length > 0) {
    content += `## Open Issues\n\n`;

    // Group by milestone
    const byMilestone = {};
    openIssues.forEach(issue => {
      const milestone = issue.milestone?.title || 'No Milestone';
      if (!byMilestone[milestone]) {
        byMilestone[milestone] = [];
      }
      byMilestone[milestone].push(issue);
    });

    for (const [milestone, issueList] of Object.entries(byMilestone)) {
      content += `### ${milestone}\n\n`;
      for (const issue of issueList) {
        const labels = issue.labels.map(l => `\`${l.name}\``).join(' ');
        content += `- [#${issue.number}](${issue.number}.md): ${issue.title} ${labels}\n`;
      }
      content += `\n`;
    }
  }

  // Usage instructions
  content += `---\n\n`;
  content += `## Usage with Claude\n\n`;
  content += `### Reading Issues\n\n`;
  content += `\`\`\`bash\n`;
  content += `# Read a specific issue\n`;
  content += `Read docs/issues/33.md\n\n`;
  content += `# View all open issues\n`;
  content += `Read docs/issues/README.md\n`;
  content += `\`\`\`\n\n`;
  content += `### Working on an Issue\n\n`;
  content += `1. Read the issue file: \`docs/issues/{number}.md\`\n`;
  content += `2. View screenshots (images are in \`docs/issues/images/\`)\n`;
  content += `3. Create a branch: \`git checkout -b issue-{number}-description\`\n`;
  content += `4. Implement changes\n`;
  content += `5. Reference issue in commit: \`Fixes #33: Description\`\n\n`;
  content += `### Syncing Issues\n\n`;
  content += `\`\`\`bash\n`;
  content += `# Manual sync (run locally)\n`;
  content += `node scripts/sync-github-issues.mjs\n\n`;
  content += `# Force re-download all images\n`;
  content += `node scripts/sync-github-issues.mjs --force-images\n`;
  content += `\`\`\`\n\n`;
  content += `**Note:** Issues are automatically synced via GitHub Actions when:\n`;
  content += `- Issues are opened/edited/closed\n`;
  content += `- Issues are labeled/unlabeled\n`;
  content += `- Comments are added\n`;
  content += `- Manual workflow dispatch\n\n`;

  // Write index
  const indexPath = join(ISSUES_DIR, 'README.md');
  writeFileSync(indexPath, content, 'utf-8');
  console.log(`✅ Saved: ${indexPath}`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Starting GitHub issues sync...\n');

  const issues = fetchIssues();

  console.log('\n📥 Downloading images and generating issue files...\n');

  for (const issue of issues) {
    await generateIssueFile(issue);
  }

  console.log('\n📋 Generating master index...\n');
  generateIndex(issues);

  if (PUSH_STATE_FROM_LOCAL) {
    console.log('\n⬆️  Pushing state changes back to GitHub...\n');
    await pushStateChangesFromLocal();
  }

  console.log('\n✅ Sync complete!\n');
  console.log(`📁 Issues: ${ISSUES_DIR}`);
  console.log(`🖼️  Images: ${IMAGES_DIR}`);
}

main().catch(error => {
  console.error('❌ Sync failed:', error);
  process.exit(1);
});

/**
 * Push local state (open/closed) back to GitHub using metadata in docs/issues/{n}.md
 * Opt-in via --push-state
 */
async function pushStateChangesFromLocal() {
  const fs = await import('fs');
  const issueFiles = fs.readdirSync(ISSUES_DIR).filter(f => f.match(/^[0-9]+\\.md$/));

  for (const file of issueFiles) {
    try {
      const filePath = join(ISSUES_DIR, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      const metaMatch = content.match(/<!-- Metadata:([\\s\\S]*?)-->/);
      if (!metaMatch) continue;

      const metaJson = metaMatch[1];
      const meta = JSON.parse(metaJson);
      const desiredState = (meta.state || '').toLowerCase();
      if (!['open', 'closed'].includes(desiredState)) continue;

      const issueNumber = meta.number;
      if (!issueNumber) continue;

      console.log(`  ↕️  Syncing state for #${issueNumber} -> ${desiredState.toUpperCase()}`);
      execSync(`gh issue edit ${issueNumber} --repo ${REPO} --state ${desiredState}`, { stdio: 'inherit' });
    } catch (error) {
      console.warn(`  ⚠️  Skipping push for ${file}: ${error.message}`);
    }
  }
}
