// this_file: review/src/Messages.tsx
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, ChevronRight, Search } from "lucide-react";
import { stateLabel, type Catalog, type Unit } from "./types";
type Props = { catalog: Catalog; filtered: Unit[]; selected: string; query: string; unreviewed: boolean; busy: boolean; onQuery: (value: string) => void; onFilter: (value: boolean) => void; onSelect: (key: string) => void; onMove: (delta: number) => void };
export function Messages(props: Props) {
  const [limit, setLimit] = useState(200);
  useEffect(() => setLimit(200), [props.query, props.unreviewed]);
  useEffect(() => { const index = props.filtered.findIndex(unit => unit.key === props.selected); if (index >= limit) setLimit(Math.ceil((index + 1) / 200) * 200); }, [props.selected, props.filtered, limit]);
  return <aside className="messages-panel" aria-label="Messages">
    <div className="messages-heading"><h2>Messages</h2><label className="search"><Search size={19} aria-hidden="true"/><input aria-label="Search source or translation" placeholder="Search source or translation" value={props.query} onChange={event => props.onQuery(event.target.value)}/></label>
    <label className="filter"><input type="checkbox" checked={props.unreviewed} onChange={event => props.onFilter(event.target.checked)}/>Unreviewed only</label>
    <div className="progress-label">{props.catalog.approved} of {props.catalog.total} approved</div><progress value={props.catalog.approved} max={props.catalog.total || 1} aria-label="Approved messages"/></div>
    <div className="messages-list">{props.filtered.slice(0, limit).map(unit => <button key={unit.key} aria-label={`${unit.source || "Empty source"}, ${unit.context || "No context"}, ${stateLabel[unit.state] ?? unit.state}`} className={`message-row ${unit.key === props.selected ? "selected" : ""}`} aria-current={unit.key === props.selected ? "true" : undefined} disabled={props.busy} onClick={() => props.onSelect(unit.key)}><span className="message-copy"><span className="message-source">{unit.source || "Empty source"}</span><span className="message-context">{unit.context || "No context"}</span></span><span className={`message-status state-${unit.state}`}><span className="status-dot"/>{stateLabel[unit.state] ?? unit.state}</span><ChevronRight size={18} aria-hidden="true"/></button>)}{props.filtered.length === 0 && <p className="empty">No matching messages.</p>}{props.filtered.length > limit && <button className="more" onClick={() => setLimit(value => value + 200)}>Show more messages</button>}</div>
    <div className="message-navigation"><button aria-label="Previous message" onClick={() => props.onMove(-1)} disabled={props.busy || props.filtered.findIndex(unit => unit.key === props.selected) <= 0}><ArrowUp size={16}/></button><span>{props.filtered.length} messages</span><button aria-label="Next message" onClick={() => props.onMove(1)} disabled={props.busy || props.filtered.findIndex(unit => unit.key === props.selected) >= props.filtered.length - 1}><ArrowDown size={16}/></button></div>
  </aside>;
}
