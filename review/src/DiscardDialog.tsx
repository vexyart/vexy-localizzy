// this_file: review/src/DiscardDialog.tsx
import { useEffect, useRef } from "react";

export function DiscardDialog({ onKeep, onDiscard }: { onKeep: () => void; onDiscard: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} role="alertdialog" aria-labelledby="discard-title" aria-describedby="discard-description" onCancel={event => { event.preventDefault(); onKeep(); }}>
    <h2 id="discard-title">Discard unsaved changes?</h2>
    <p id="discard-description">Your draft has not been saved. Keep editing to preserve it.</p>
    <div className="dialog-actions"><button autoFocus onClick={onKeep}>Keep editing</button><button className="danger" onClick={onDiscard}>Discard changes</button></div>
  </dialog>;
}
