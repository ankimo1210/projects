"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { loadMeta, loadSnapshot, type Meta } from "@/lib/data";
type MetaState = {
  meta: Meta | null;
  error: Error | null;
  loading: boolean;
  revision: number;
  reload: () => void;
};
const DataContext = createContext<MetaState>({
  meta: null,
  error: null,
  loading: true,
  revision: 0,
  reload: () => {},
});
export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{
    meta: Meta | null;
    error: Error | null;
    loading: boolean;
  }>({ meta: null, error: null, loading: true });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    loadMeta(fetch, abort.signal)
      .then((meta) => {
        if (!abort.signal.aborted)
          setState({ meta, error: null, loading: false });
      })
      .catch((error) => {
        if (!abort.signal.aborted)
          setState({ meta: null, error, loading: false });
      });
    return () => abort.abort();
  }, [revision]);
  const reload = () => {
    setState({ meta: null, error: null, loading: true });
    setRevision((r) => r + 1);
  };
  return (
    <DataContext value={{ ...state, revision, reload }}>{children}</DataContext>
  );
}
export const useMeta = () => useContext(DataContext);
export function useSnapshot<T>(name: string, validate: (v: unknown) => v is T) {
  const { meta, error: metaError, loading: metaLoading, revision } = useMeta();
  const key = meta ? `${revision}:${meta.generation}:${name}` : "";
  const [state, setState] = useState<{
    key: string;
    data: T | null;
    error: Error | null;
  }>({ key: "", data: null, error: null });
  useEffect(() => {
    if (!meta || !name) return;
    const abort = new AbortController();
    loadSnapshot(meta, name, validate, fetch, abort.signal)
      .then((data) => {
        if (!abort.signal.aborted) setState({ key, data, error: null });
      })
      .catch((error) => {
        if (!abort.signal.aborted) setState({ key, data: null, error });
      });
    return () => abort.abort();
  }, [meta, name, validate, key]);
  return {
    data: state.key === key ? state.data : null,
    error: metaError || (state.key === key ? state.error : null),
    loading: metaLoading || (!metaError && Boolean(name) && state.key !== key),
  };
}
