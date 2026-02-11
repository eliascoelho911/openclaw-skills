import type { Plugin } from "@opencode-ai/plugin";

/**
 * Pre-commit hook plugin for OpenCode
 *
 * Runs the following checks before any git commit:
 * - uv run ruff check --fix (on staged Python files)
 * - uv run pytest --tb=short -q --no-header -rF
 *
 * If any check fails, the commit is blocked with an error message.
 */
export const PreCommitHook: Plugin = async ({ $, directory }) => {
  return {
    "tool.execute.before": async (input, output) => {
      // Only intercept git commit commands
      if (input.tool !== "bash") return;

      const command = output.args.command as string;
      if (!command) return;

      // Check if this is a git commit command
      const isGitCommit = /\bgit\s+commit\b/.test(command);
      if (!isGitCommit) return;

      console.log("[pre-commit] Running pre-commit checks...");

      // Get staged Python files
      const stagedFilesResult =
        await $`git diff --cached --name-only --diff-filter=ACM -- "*.py"`.quiet();
      const stagedFiles = stagedFilesResult.stdout.toString().trim();

      if (stagedFiles) {
        const files = stagedFiles.split("\n").filter(Boolean);
        console.log(`[pre-commit] Found ${files.length} staged Python file(s)`);

        // Run ruff check with --fix on staged files
        console.log("[pre-commit] Running: uv run ruff check --fix");
        try {
          const ruffResult =
            await $`uv run ruff check ${files} --fix`.quiet();
          console.log("[pre-commit] Ruff check passed");

          // Check if ruff modified any files
          const modifiedResult =
            await $`git diff --name-only -- ${files}`.quiet();
          const modifiedFiles = modifiedResult.stdout.toString().trim();

          if (modifiedFiles) {
            console.log(
              "[pre-commit] Ruff fixed some issues. Re-staging modified files...",
            );
            const filesToStage = modifiedFiles.split("\n").filter(Boolean);
            await $`git add ${filesToStage}`;
          }
        } catch (error: unknown) {
          const errorMessage =
            error instanceof Error ? error.message : String(error);
          const stderr =
            error && typeof error === "object" && "stderr" in error
              ? String((error as { stderr: unknown }).stderr)
              : "";
          throw new Error(
            `[pre-commit] Ruff check failed. Please fix the issues before committing.\n${stderr || errorMessage}`,
          );
        }
      } else {
        console.log("[pre-commit] No staged Python files to check with ruff");
      }

      // Run pytest
      console.log(
        "[pre-commit] Running: uv run pytest --tb=short -q --no-header -rF",
      );
      try {
        await $`uv run pytest --tb=short -q --no-header -rF`.quiet();
        console.log("[pre-commit] Tests passed");
      } catch (error: unknown) {
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        const stdout =
          error && typeof error === "object" && "stdout" in error
            ? String((error as { stdout: unknown }).stdout)
            : "";
        const stderr =
          error && typeof error === "object" && "stderr" in error
            ? String((error as { stderr: unknown }).stderr)
            : "";
        throw new Error(
          `[pre-commit] Tests failed. Please fix failing tests before committing.\n${stdout || stderr || errorMessage}`,
        );
      }

      console.log("[pre-commit] All checks passed!");
    },
  };
};
