import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const puppeteerConfigPath = path.join(__dirname, "puppeteer-config.json");
const mmdcBinary = path.join(
  repoRoot,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "mmdc.cmd" : "mmdc",
);

const ignoredDirs = new Set([
  ".git",
  ".venv",
  ".pytest_cache",
  "__pycache__",
  "node_modules",
]);

function toPosixPath(filePath) {
  return filePath.split(path.sep).join("/");
}

function countLines(input) {
  if (!input) {
    return 1;
  }

  return input.split(/\r?\n/).length;
}

async function walk(dirPath, collected = []) {
  const entries = await fs.readdir(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    if (ignoredDirs.has(entry.name)) {
      continue;
    }

    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      await walk(fullPath, collected);
      continue;
    }

    const ext = path.extname(entry.name).toLowerCase();
    if (ext === ".md" || ext === ".mdx" || ext === ".mmd") {
      collected.push(fullPath);
    }
  }

  return collected;
}

function extractMarkdownDiagrams(content, filePath) {
  const diagrams = [];
  const mermaidFence = /```mermaid\s*\n([\s\S]*?)```/g;
  let match;
  let index = 0;

  while ((match = mermaidFence.exec(content)) !== null) {
    index += 1;
    const before = content.slice(0, match.index);
    const startLine = countLines(before);
    diagrams.push({
      id: `${toPosixPath(path.relative(repoRoot, filePath))}#${index}`,
      filePath,
      startLine,
      source: match[1].trim(),
    });
  }

  return diagrams;
}

async function collectDiagrams(pathsToScan) {
  const diagrams = [];

  for (const filePath of pathsToScan) {
    const ext = path.extname(filePath).toLowerCase();
    const content = await fs.readFile(filePath, "utf8");

    if (ext === ".mmd") {
      diagrams.push({
        id: toPosixPath(path.relative(repoRoot, filePath)),
        filePath,
        startLine: 1,
        source: content.trim(),
      });
      continue;
    }

    diagrams.push(...extractMarkdownDiagrams(content, filePath));
  }

  return diagrams;
}

function resolveInputTargets(cliArgs) {
  if (cliArgs.length === 0) {
    return walk(repoRoot);
  }

  return Promise.all(
    cliArgs.map(async (entry) => path.resolve(repoRoot, entry)),
  );
}

function renderDiagram(tempDir, diagram, index) {
  const inputPath = path.join(tempDir, `diagram-${index + 1}.mmd`);
  const outputPath = path.join(tempDir, `diagram-${index + 1}.svg`);

  return fs
    .writeFile(inputPath, `${diagram.source}\n`, "utf8")
    .then(() =>
      spawnSync(
        mmdcBinary,
        ["-p", puppeteerConfigPath, "-i", inputPath, "-o", outputPath],
        {
          cwd: repoRoot,
          encoding: "utf8",
        },
      ),
    )
    .then((result) => ({ ...result, inputPath, outputPath }));
}

async function main() {
  try {
    await fs.access(mmdcBinary);
  } catch {
    console.error(`mmdc not found at ${mmdcBinary}`);
    process.exit(1);
  }

  const cliArgs = process.argv.slice(2);
  const pathsToScan = await resolveInputTargets(cliArgs);
  const diagrams = await collectDiagrams(pathsToScan);

  if (diagrams.length === 0) {
    console.error("No Mermaid diagrams found.");
    process.exit(1);
  }

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "mermaid-verify-"));
  const failures = [];

  try {
    for (let index = 0; index < diagrams.length; index += 1) {
      const diagram = diagrams[index];
      const relativeFilePath = toPosixPath(path.relative(repoRoot, diagram.filePath));
      const result = await renderDiagram(tempDir, diagram, index);

      if (result.status !== 0) {
        failures.push({
          diagram,
          stderr: result.stderr?.trim() || "Unknown mmdc error",
          stdout: result.stdout?.trim() || "",
        });
        continue;
      }

      console.log(`OK ${relativeFilePath}:${diagram.startLine}`);
    }

    if (failures.length > 0) {
      console.error(`Mermaid validation failed for ${failures.length} diagram(s).`);
      for (const failure of failures) {
        const relativeFilePath = toPosixPath(
          path.relative(repoRoot, failure.diagram.filePath),
        );
        console.error(`- ${relativeFilePath}:${failure.diagram.startLine}`);
        if (failure.stderr) {
          console.error(failure.stderr);
        }
        if (failure.stdout) {
          console.error(failure.stdout);
        }
      }
      console.error(`Rendered inputs kept at ${tempDir}`);
      process.exit(1);
    }

    await fs.rm(tempDir, { recursive: true, force: true });
    console.log(`Validated ${diagrams.length} Mermaid diagram(s).`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    console.error(`Rendered inputs kept at ${tempDir}`);
    process.exit(1);
  }
}

await main();
