import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { Landing } from "../src/features/landing/Landing";

const meta = {
  title: "Landing/Landing",
  component: Landing,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof Landing>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {};
