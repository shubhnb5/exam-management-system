import { createContext, useCallback, useContext, useRef, useState } from "react";
import Modal from "./Modal";

const DialogContext = createContext(null);

export function DialogProvider({ children }) {
  const [state, setState] = useState(null);
  const inputValue = useRef("");

  const finish = useCallback((result) => {
    setState((current) => {
      current?.resolve(result);
      return null;
    });
  }, []);

  const confirm = useCallback((options) => {
    return new Promise((resolve) => {
      setState({ kind: "confirm", ...options, resolve });
    });
  }, []);

  const promptText = useCallback((options) => {
    inputValue.current = options.defaultValue || "";
    return new Promise((resolve) => {
      setState({ kind: "prompt", ...options, resolve });
    });
  }, []);

  return (
    <DialogContext.Provider value={{ confirm, promptText }}>
      {children}
      {state && (
        <Modal title={state.title} onClose={() => finish(state.kind === "prompt" ? null : false)}>
          {state.message && <p className="modal-message">{state.message}</p>}
          {state.kind === "prompt" && (
            <input
              type={state.inputType || "text"}
              className="modal-input"
              autoFocus
              defaultValue={state.defaultValue || ""}
              placeholder={state.inputLabel}
              onChange={(e) => {
                inputValue.current = e.target.value;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") finish(inputValue.current);
              }}
            />
          )}
          <div className="modal-actions">
            <button
              type="button"
              className="btn-small"
              onClick={() => finish(state.kind === "prompt" ? null : false)}
            >
              {state.cancelText || "Cancel"}
            </button>
            <button
              type="button"
              className={`btn-small ${state.danger ? "btn-danger" : ""}`}
              onClick={() => finish(state.kind === "prompt" ? inputValue.current : true)}
            >
              {state.confirmText || "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </DialogContext.Provider>
  );
}

export function useDialog() {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error("useDialog must be used within a DialogProvider");
  return ctx;
}
