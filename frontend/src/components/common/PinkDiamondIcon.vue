<script setup lang="ts">
interface Props {
  size?: number | string
  title?: string
}

withDefaults(defineProps<Props>(), {
  size: 20,
  title: '钻石',
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-hidden="true"
  >
    <title>{{ title }}</title>
    <path
      d="M7.5 3.5H16.5L21 9L12 21L3 9L7.5 3.5Z"
      fill="#FF76B5"
      stroke="#FF3D9A"
      stroke-width="1.25"
      stroke-linejoin="round"
    />
    <path
      d="M7.5 3.5L3 9H21L16.5 3.5"
      stroke="#FFC2DC"
      stroke-width="1.25"
      stroke-linejoin="round"
      opacity="0.9"
    />
    <path
      d="M12 21L8.5 9L12 3.5L15.5 9L12 21Z"
      stroke="#FFD7E8"
      stroke-width="1.25"
      stroke-linejoin="round"
      opacity="0.85"
    />
  </svg>
</template>

