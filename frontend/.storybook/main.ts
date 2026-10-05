import type { StorybookConfig } from "@storybook/nextjs-vite";
import { vanillaExtractPlugin } from "@vanilla-extract/vite-plugin";

const config: StorybookConfig = {
  stories: ["../stories/**/*.stories.@(ts|tsx)"],
  addons: [],
  framework: { name: "@storybook/nextjs-vite", options: {} },
  // Mismo plugin de Vanilla Extract que usa Vitest (D-019).
  viteFinal: (viteConfig) => {
    viteConfig.plugins = [...(viteConfig.plugins ?? []), vanillaExtractPlugin()];
    return viteConfig;
  },
};

export default config;
