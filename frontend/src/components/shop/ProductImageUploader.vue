<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { Image, Upload, RefreshCw, Trash2 } from 'lucide-vue-next'

import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { shopApi } from '@/utils/api'
import { useUIStore } from '@/stores/ui'

interface Props {
  modelValue: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const uiStore = useUIStore()

const fileInput = ref<HTMLInputElement | null>(null)
const cropImageEl = ref<HTMLImageElement | null>(null)

const modalOpen = ref(false)
const rawObjectUrl = ref<string | null>(null)
const rawFilename = ref<string>('product.jpg')

const cropper = ref<Cropper | null>(null)
const isUploading = ref(false)

const OUTPUT_WIDTH = 800
const OUTPUT_HEIGHT = 512
const OUTPUT_ASPECT_RATIO = OUTPUT_WIDTH / OUTPUT_HEIGHT

function openFilePicker() {
  fileInput.value?.click()
}

function revokeObjectUrl() {
  if (rawObjectUrl.value) {
    URL.revokeObjectURL(rawObjectUrl.value)
    rawObjectUrl.value = null
  }
}

function destroyCropper() {
  cropper.value?.destroy()
  cropper.value = null
}

async function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''

  if (!file) return

  if (!file.type.startsWith('image/')) {
    uiStore.showError('请选择图片文件')
    return
  }

  revokeObjectUrl()
  rawFilename.value = file.name || 'product.jpg'
  rawObjectUrl.value = URL.createObjectURL(file)
  modalOpen.value = true
}

function removeImage() {
  emit('update:modelValue', '')
}

function blobFromCanvas(canvas: HTMLCanvasElement, mime = 'image/jpeg', quality = 0.9) {
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) return reject(new Error('生成图片失败'))
      resolve(blob)
    }, mime, quality)
  })
}

async function uploadCropped() {
  if (!cropper.value) return
  if (isUploading.value) return

  isUploading.value = true
  try {
    const canvas = cropper.value.getCroppedCanvas({
      width: OUTPUT_WIDTH,
      height: OUTPUT_HEIGHT,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high',
    })
    const blob = await blobFromCanvas(canvas, 'image/jpeg', 0.92)

    const resp = await shopApi.uploadProductImage(blob, rawFilename.value)
    const url = resp.data?.data?.url || resp.data?.url
    if (!url || typeof url !== 'string') {
      throw new Error('上传返回缺少 url')
    }

    emit('update:modelValue', url)
    modalOpen.value = false
    uiStore.showSuccess('图片已更新')
  } catch (e: any) {
    uiStore.showError(e?.response?.data?.detail || e?.message || '上传失败')
  } finally {
    isUploading.value = false
  }
}

watch(modalOpen, async (isOpen) => {
  if (!isOpen) {
    destroyCropper()
    revokeObjectUrl()
    return
  }

  await nextTick()
  destroyCropper()

  if (!cropImageEl.value) return
  cropper.value = new Cropper(cropImageEl.value, {
    aspectRatio: OUTPUT_ASPECT_RATIO,
    viewMode: 1,
    autoCropArea: 1,
    background: false,
    responsive: true,
    movable: true,
    zoomable: true,
    rotatable: false,
    scalable: false,
    guides: false,
    center: true,
    preview: '.product-image-uploader__crop-preview',
  })
})

onBeforeUnmount(() => {
  destroyCropper()
  revokeObjectUrl()
})
</script>

<template>
  <div class="product-image-uploader">
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="product-image-uploader__file"
      @change="onFileChange"
    />

    <div class="product-image-uploader__header">
      <div class="product-image-uploader__label">
        <Image :size="18" class="product-image-uploader__icon" />
        商品图片 (可选)
      </div>

      <div class="product-image-uploader__actions">
        <BaseButton
          type="button"
          variant="secondary"
          size="sm"
          @click="openFilePicker"
        >
          <Upload :size="16" />
          {{ props.modelValue ? '更换图片' : '上传图片' }}
        </BaseButton>

        <BaseButton
          v-if="props.modelValue"
          type="button"
          variant="ghost"
          size="sm"
          @click="removeImage"
        >
          <Trash2 :size="16" />
          移除
        </BaseButton>
      </div>
    </div>

    <p class="product-image-uploader__hint">
      支持上传本地图片，可裁剪成商品封面比例
    </p>

    <div v-if="props.modelValue" class="product-image-uploader__preview">
      <img :src="props.modelValue" alt="商品图片预览" />
    </div>

    <BaseModal
      v-model="modalOpen"
      title="裁剪商品图片"
      size="lg"
      :closable="!isUploading"
      :close-on-backdrop="!isUploading"
    >
      <div class="product-image-uploader__crop">
        <div class="product-image-uploader__crop-main">
          <img
            v-if="rawObjectUrl"
            ref="cropImageEl"
            :src="rawObjectUrl"
            alt="裁剪"
            class="product-image-uploader__crop-img"
          />
        </div>

        <div class="product-image-uploader__crop-side">
          <div class="product-image-uploader__crop-title">预览</div>
          <div class="product-image-uploader__crop-preview" />

          <div class="product-image-uploader__crop-tip">
            <RefreshCw :size="14" />
            可拖拽图片、滚轮/双指缩放调整
          </div>
        </div>
      </div>

      <template #footer>
        <div class="product-image-uploader__footer">
          <BaseButton
            type="button"
            variant="secondary"
            :disabled="isUploading"
            @click="modalOpen = false"
          >
            取消
          </BaseButton>
          <BaseButton
            type="button"
            variant="primary"
            :loading="isUploading"
            @click="uploadCropped"
          >
            裁剪并上传
          </BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.product-image-uploader {
  &__file {
    display: none;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $spacing-md;
    margin-bottom: $spacing-sm;
  }

  &__label {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-small;
    font-weight: $font-weight-medium;
    color: $text-secondary;
  }

  &__icon {
    color: $text-secondary;
  }

  &__actions {
    display: flex;
    gap: $spacing-sm;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  &__hint {
    font-size: $font-size-caption;
    color: $text-light;
    margin-bottom: $spacing-md;
  }

  &__preview {
    width: 240px;
    height: 154px;
    border-radius: $radius-lg;
    overflow: hidden;
    border: 2px dashed rgba($text-secondary, 0.25);
    background: rgba($cream, 0.3);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
  }

  &__crop {
    display: grid;
    grid-template-columns: 1fr 220px;
    gap: $spacing-lg;
    align-items: start;

    @include tablet {
      grid-template-columns: 1fr;
    }
  }

  &__crop-main {
    min-height: 360px;
    background: rgba($text-secondary, 0.06);
    border-radius: $radius-lg;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__crop-img {
    max-width: 100%;
    display: block;
  }

  &__crop-side {
    display: flex;
    flex-direction: column;
    gap: $spacing-md;
  }

  &__crop-title {
    font-weight: $font-weight-medium;
    color: $text-secondary;
    font-size: $font-size-small;
  }

  &__crop-preview {
    width: 200px;
    height: 128px;
    border-radius: $radius-lg;
    overflow: hidden;
    border: 1px solid rgba($text-secondary, 0.15);
    background: rgba($cream, 0.3);

    @include tablet {
      width: 160px;
      height: 102px;
    }
  }

  &__crop-tip {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    font-size: $font-size-caption;
    color: $text-light;
  }

  &__footer {
    width: 100%;
    display: flex;
    justify-content: flex-end;
    gap: $spacing-sm;
  }
}
</style>
