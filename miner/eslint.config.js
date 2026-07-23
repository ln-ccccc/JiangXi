import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'uploads/**', 'change_matrix_outputs/**'],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      globals: {
        Buffer: 'readonly',
        alert: 'readonly',
        Blob: 'readonly',
        console: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        process: 'readonly',
        setTimeout: 'readonly',
        URL: 'readonly',
        window: 'readonly',
      },
    },
    rules: {
      'no-empty': 'warn',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/multi-word-component-names': 'off',
    },
  },
];
