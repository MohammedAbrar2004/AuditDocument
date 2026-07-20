interface ChecklistItemLike {
  item_id: string | null;
  text: string;
}

interface ItemListProps {
  items: ChecklistItemLike[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function ItemList({ items, currentIndex, onSelect }: ItemListProps) {
  return (
    <div className="item-list panel">
      {items.map((item, idx) => (
        <button
          key={`${item.item_id ?? "null"}-${idx}`}
          className={idx === currentIndex ? "item-row active" : "item-row"}
          onClick={() => onSelect(idx)}
        >
          {item.item_id && <span className="item-id">{item.item_id}</span>}
          <span className="item-text">{item.text}</span>
        </button>
      ))}
    </div>
  );
}
