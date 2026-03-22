import type ModelViewerWrapper from './ModelViewerWrapper.vue';

/**
 * Type guard that returns true only when the viewer ref is pointing at the
 * fully-resolved inner component (not the async wrapper rendered while loading).
 *
 * Background: `ModelViewerWrapper` is loaded via `defineAsyncComponent`. Before
 * the inner component resolves, Vue may briefly set the template ref to the
 * async component wrapper, which does not expose `onElemReady`, `setPosterText`,
 * etc. Checking for `onElemReady` (the sentinel method) lets callers distinguish
 * the two states without relying on `as any` at every call site.
 */
export function isViewerReady(viewer: unknown): viewer is InstanceType<typeof ModelViewerWrapper> {
  return !!viewer && typeof (viewer as Record<string, unknown>).onElemReady === 'function';
}
