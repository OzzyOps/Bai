// The shared config lives in @bai/config so every app lints identically.
// It needs type information (typescript-eslint's strictTypeChecked rules), and
// type information is per-project — hence this thin wrapper rather than a
// single config at the repo root.
import shared from '@bai/config/eslint';

export default [
  ...shared,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  { ignores: ['dist/**', 'node_modules/**', '*.config.js'] },
];
