// Custom type declarations for react-window (no bundled .d.ts in v1.8.x)
declare module 'react-window' {
  import type { ComponentType, CSSProperties } from 'react'

  export interface ListChildComponentProps {
    index: number
    style: CSSProperties
    data: unknown
  }

  export interface VariableSizeListProps {
    children: ComponentType<ListChildComponentProps>
    height: number
    itemCount: number
    itemSize: (index: number) => number
    width: number | string
    itemData?: unknown
    className?: string
    style?: CSSProperties
    overscanCount?: number
    onScroll?: (props: { scrollDirection: 'forward' | 'backward'; scrollOffset: number; scrollUpdateWasRequested: boolean }) => void
  }

  export class VariableSizeList extends React.Component<VariableSizeListProps> {
    scrollToItem(index: number, align?: 'auto' | 'smart' | 'center' | 'start' | 'end'): void
    scrollTo(scrollOffset: number): void
    resetAfterIndex(index: number, shouldForceUpdate?: boolean): void
  }

  export interface FixedSizeListProps {
    children: ComponentType<ListChildComponentProps>
    height: number
    itemCount: number
    itemSize: number
    width: number | string
    itemData?: unknown
    className?: string
    style?: CSSProperties
    overscanCount?: number
  }

  export class FixedSizeList extends React.Component<FixedSizeListProps> {
    scrollToItem(index: number, align?: 'auto' | 'smart' | 'center' | 'start' | 'end'): void
    scrollTo(scrollOffset: number): void
  }
}
