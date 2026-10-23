const base = { width: 26, height: 26, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };

export function Sprout(p) {
  return (<svg {...base} {...p}><path d="M12 22V12" /><path d="M12 12C12 8 9 5 4 5c0 4 3 7 8 7" /><path d="M12 14c0-3 2.5-6 8-6 0 4-3 6-8 6" /></svg>);
}
export function Leaf(p) {
  return (<svg {...base} {...p}><path d="M5 19C5 10 10 5 20 5c0 10-5 15-14 15" /><path d="M5 19l8-8" /></svg>);
}
export function Wheat(p) {
  return (<svg {...base} {...p}><path d="M12 22V8" /><path d="M12 8c-2-1-3-3-3-5 2 0 3 2 3 5" /><path d="M12 8c2-1 3-3 3-5-2 0-3 2-3 5" /><path d="M12 13c-2-1-4-3-4-5" /><path d="M12 13c2-1 4-3 4-5" /><path d="M12 18c-2-1-4-3-4-5" /><path d="M12 18c2-1 4-3 4-5" /></svg>);
}
export function Trend(p) {
  return (<svg {...base} {...p}><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></svg>);
}
export function Logo(p) {
  return (<svg {...base} width={20} height={20} strokeWidth={2.2} {...p}><path d="M12 22V11" /><path d="M12 11C12 6 9 3 4 3c0 5 3 8 8 8" /><path d="M12 14c0-4 3-7 8-7 0 5-3 7-8 7" /></svg>);
}
export function Chat(p) {
  return (<svg {...base} width={20} height={20} {...p}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" /></svg>);
}
export function Menu(p) {
  return (<svg {...base} width={20} height={20} {...p}><path d="M4 7h16M4 12h16M4 17h16" /></svg>);
}
export function Chevron(p) {
  return (<svg {...base} width={16} height={16} {...p}><path d="M6 9l6 6 6-6" /></svg>);
}
export function SignOut(p) {
  return (<svg {...base} width={18} height={18} {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5" /><path d="M21 12H9" /></svg>);
}
export function Grid(p) {
  return (<svg {...base} width={22} height={22} {...p}><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>);
}
export function Bars(p) {
  return (<svg {...base} width={22} height={22} {...p}><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M22 20H2" /></svg>);
}
export function Globe(p) {
  return (<svg {...base} width={22} height={22} {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3c3 3 3 15 0 18" /><path d="M12 3c-3 3-3 15 0 18" /></svg>);
}
