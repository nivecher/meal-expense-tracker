// Commit message conventions based on Conventional Commits
// https://www.conventionalcommits.org/

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',     // New feature
        'fix',      // Bug fix
        'docs',     // Documentation changes
        'style',    // Code style changes (formatting, missing semi-colons, etc.)
        'refactor', // Code refactoring
        'test',     // Adding or modifying tests
        'chore',    // Build process or auxiliary tool changes
        'ci',       // CI/CD related changes
        'perf',     // Performance improvements
        'revert',   // Revert a previous commit
        'wip',      // Work in progress
      ],
    ],
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
    'scope-case': [2, 'always', 'lower-case'],
    'subject-case': [2, 'always', 'sentence-case'],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 72],
    'body-leading-blank': [1, 'always'],
    'body-max-line-length': [2, 'always', 200],
    'footer-leading-blank': [1, 'always'],
    'footer-max-line-length': [2, 'always', 72],
  },
  helpUrl:
    'https://github.com/conventional-changelog/commitlint/#what-is-commitlint',
};
