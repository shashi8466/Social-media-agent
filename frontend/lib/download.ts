/**
 * Download a remote file reliably, even across origins.
 *
 * The HTML `<a download>` attribute is IGNORED by browsers for cross-origin URLs
 * (e.g. the frontend on :3000 linking to images served from the API on :8000) —
 * the browser just navigates to the file instead of saving it. To work around
 * this we fetch the file as a Blob, create a same-origin object URL, and click a
 * synthesized anchor. The backend has open CORS so the fetch succeeds.
 */
export async function downloadFile(url: string, filename: string): Promise<void> {
  try {
    const res = await fetch(url, { mode: 'cors' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = filename || 'download';
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Revoke after a tick so the download has a chance to start
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
  } catch (e) {
    // Last-resort fallback: open the file in a new tab so the user can save it
    console.error('Download failed, opening in new tab:', e);
    window.open(url, '_blank', 'noopener');
  }
}
