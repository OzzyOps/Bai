import js from '@eslint/js';
import ts from 'typescript-eslint';
import react from 'eslint-plugin-react-hooks';
import a11y from 'eslint-plugin-jsx-a11y';

export default ts.config(
  js.configs.recommended,
  ...ts.configs.strictTypeChecked,
  {
    plugins: { 'react-hooks': react, 'jsx-a11y': a11y },
    rules: {
      ...react.configs.recommended.rules,
      ...a11y.configs.recommended.rules,
      // Accessibility is a floor, not a preference — these are errors.
      'jsx-a11y/no-autofocus': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      // Money is minor units + ISO 4217. A raw float in a money context is a bug.
      'no-restricted-syntax': ['error', {
        selector: "CallExpression[callee.object.name='Number'][callee.property.name='parseFloat']",
        message: 'Money is integer minor units. Use @bai/ui formatMoney, never parseFloat.',
      }],
    },
  },
  { ignores: ['dist/**', 'node_modules/**', '**/dist/**'] },
);
