# Git Workflow

## Resolving Merge Conflicts

When you encounter a merge conflict:

1. Open the conflicting files
2. Look for conflict markers: <<<<<<<, =======, >>>>>>>
3. Choose which changes to keep or combine them
4. Remove the conflict markers
5. Stage the resolved files: `git add <file>`
6. Complete the merge: `git commit`

## Creating Branches

Use `git checkout -b <branch-name>` to create and switch to a new branch.
