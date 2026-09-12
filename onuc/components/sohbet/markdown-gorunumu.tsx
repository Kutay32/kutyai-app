"use client";

import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { KodBlogu } from "./kod-blogu";

/**
 * Sohbet yanıtlarının markdown gösterimi.
 *
 * `rehype-raw` bilinçli olarak kullanılmaz: ham HTML yorumlanmadığı için model
 * çıktısından gelen etiketler XSS vektörü olamaz.
 */
const bilesenler: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children, node, ...kalan }) => {
    const metin = String(children).replace(/\n$/, "");
    const blokMu = /language-/.test(className ?? "") || metin.includes("\n");
    if (!blokMu) {
      return (
        <code
          className="rounded-md border border-neutral-200 bg-neutral-50 px-1 py-0.5 font-mono text-[0.85em]"
          {...kalan}
        >
          {children}
        </code>
      );
    }
    const dil = /language-([\w+#.-]+)/.exec(className ?? "")?.[1] ?? null;
    return <KodBlogu dil={dil} metin={metin} />;
  },
  p: ({ node, ...kalan }) => <p className="mb-3 text-sm leading-relaxed last:mb-0" {...kalan} />,
  a: ({ node, ...kalan }) => (
    <a
      className="underline underline-offset-2 hover:text-neutral-700"
      target="_blank"
      rel="noopener noreferrer"
      {...kalan}
    />
  ),
  strong: ({ node, ...kalan }) => <strong className="font-medium" {...kalan} />,
  ul: ({ node, ...kalan }) => (
    <ul className="mb-3 list-disc space-y-1 pl-5 text-sm leading-relaxed" {...kalan} />
  ),
  ol: ({ node, ...kalan }) => (
    <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm leading-relaxed" {...kalan} />
  ),
  blockquote: ({ node, ...kalan }) => (
    <blockquote
      className="mb-3 border-l-2 border-neutral-200 pl-3 text-sm text-neutral-600 italic"
      {...kalan}
    />
  ),
  hr: ({ node, ...kalan }) => <hr className="my-4 border-neutral-200" {...kalan} />,
  h1: ({ node, ...kalan }) => (
    <h1 className="mt-4 mb-3 text-lg font-medium first:mt-0" {...kalan} />
  ),
  h2: ({ node, ...kalan }) => (
    <h2 className="mt-4 mb-2 text-base font-medium first:mt-0" {...kalan} />
  ),
  h3: ({ node, ...kalan }) => (
    <h3 className="mt-3 mb-2 text-sm font-semibold first:mt-0" {...kalan} />
  ),
  table: ({ node, ...kalan }) => (
    <div className="mb-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...kalan} />
    </div>
  ),
  th: ({ node, ...kalan }) => (
    <th className="border-b border-neutral-200 px-3 py-2 text-left font-medium" {...kalan} />
  ),
  td: ({ node, ...kalan }) => (
    <td className="border-b border-neutral-100 px-3 py-2 align-top" {...kalan} />
  ),
  img: ({ node, ...kalan }) => (
    <img className="max-w-full rounded-lg border border-neutral-200" {...kalan} />
  ),
};

export function MarkdownGorunumu({ icerik }: { icerik: string }) {
  return (
    <Markdown remarkPlugins={[remarkGfm]} components={bilesenler}>
      {icerik}
    </Markdown>
  );
}
