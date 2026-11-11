"use client";

import { Button } from "./ui/button";

import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowLeft, ArrowUpRight, AudioWaveform, ChevronRight, RefreshCw, Search } from "lucide-react";
import Investigation from "./investigation";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Snapshot = "initial" | "refreshed";
type Basis = "reported" | "normalized";
type Money = Record<Basis, number>;
type Monthly = Money & {month: string};
type Group = Money & {group: string; delta: number | null; normalized_delta: number | null; customer_count: number; flagged: boolean};
type Overview = Monthly & {
  cutoff: string; previous_month: string | null; delta: number | null; normalized_delta: number | null;
  trend: Monthly[]; months: string[]; groups: Group[];
};
type Contract = Money & { contract_id: string; customer_id: string; plan: string };
type Detail = Money & { contract_id: string; starts: string; ends: string; observed_count: number; missing_count: number;
  completed_margin: number | null; adjustments: { evidence_id: string; posting_month: string; service_month: string; component: string; cost_cents: number }[]; months: (Monthly & Record<string, string | number>)[] };
type Listing = {items: Contract[]; has_more: boolean};

const groups: Record<string, string> = {solar:"Solar", high_winter:"High Winter Usage", low_winter:"Low Winter Usage", unclassified:"Unclassified"};
const usd = new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"});
const monthLabel = (value: string) => new Intl.DateTimeFormat("en-US", {month:"short", year:"numeric", timeZone:"UTC"}).format(new Date(value));
const dollars = (cents: number) => usd.format(cents / 100);
const signed = (value: number | null) => value === null ? "—" : (value < 0 ? "−" : value > 0 ? "+" : "") + dollars(Math.abs(value));
const query = (params: Record<string,string>) => new URLSearchParams(params).toString();

function useData<T>(path: string | null) {
  const [result, setResult] = useState<{path: string; data?:T; error?: string}>();
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    fetch(path, {signal: controller.signal, cache: "no-store"})
      .then(async (response) => {
        if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Request failed");
        return response.json() as Promise<T>;
      })
      .then(data => setResult({path, data}))
      .catch((error) => { if (!controller.signal.aborted) setResult({path, error: String(error.message)}); });
    return () => controller.abort();
  }, [path]);
  return result?.path === path ? result : undefined;
}

function Movement({value}: {value:number|null}) {
  return <span className={value === null || value === 0 ? "muted" : value < 0 ? "negative" : "positive"}>{signed(value)}</span>;
}

function WorkspaceHeader() {
  return <header className="topbar">
    <a className="brand" href="/" aria-label="Watt home">
      <span className="brand-icon"><AudioWaveform size={20} aria-hidden="true"/></span>
      watt
    </a>
    <nav aria-label="Main navigation"><a className="nav-link" href="/">Portfolio</a></nav>
  </header>;
}

export default function Portfolio() {
  const [runId, setRunId] = useState("");
  const [startError, setStartError] = useState("");
  const [starting, setStarting] = useState(false);
  const [investigationGroup, setInvestigationGroup] = useState("solar");
  useEffect(() => {setRunId(new URLSearchParams(window.location.search).get("run") ?? "");},[]);
  const showRun = (id:string) => {
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("run",id); else url.searchParams.delete("run");
    window.history.replaceState(null,"",url);
    setRunId(id);
    window.scrollTo(0, 0);
  };
  const [snapshot, setSnapshot] = useState<Snapshot>("initial");
  const [basis, setBasis] = useState<Basis>("reported");
  const [month, setMonth] = useState("");
  const [group, setGroup] = useState("");
  const [contract, setContract] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [monthDetail, setMonthDetail] = useState("");
  const portfolio = useData<Overview>("/api/portfolio?" + query({snapshot, ...(month ? {month} : {}), retry:String(retry)}));
  const data = portfolio?.data;
  const selectedInvestigationGroup = data?.groups.find(row => row.group === investigationGroup)?.group
    ?? data?.groups[0]?.group ?? "";
  const listing = useData<Listing>(data && group && !contract ?
    "/api/contracts?" + query({snapshot, month:data.month, group, q:search, offset:String(offset)}) : null);
  const details = useData<Detail>(contract ? "/api/contracts/" + encodeURIComponent(contract) + "?" + query({snapshot}) : null);
  const detail = details?.data;
  const selectSnapshot = (value: Snapshot) => {setSnapshot(value);setMonth("");setGroup("");setContract("");setOffset(0);setSearch("");};
  const resetGroup = () => {setGroup("");setSearch("");setOffset(0);};
  const groupDelta = (g:Group) => basis === "reported" ? g.delta : g.normalized_delta;
  const movement = data ? (basis === "reported" ? data.delta : data.normalized_delta) : null;
  const focusedMonth = detail?.months.find(row => row.month === monthDetail);
  const focusedAdjustments = detail?.adjustments.filter(row => row.posting_month === monthDetail) ?? [];

  async function startRun(customerGroup:string) {
    if (!data) return;
    setStarting(true);setStartError("");
    try {
      const response=await fetch("/api/investigations",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({snapshot,month:data.month,group:customerGroup})});
      if(!response.ok) throw new Error((await response.json()).detail ?? "Unable to start the investigation");
      showRun((await response.json()).id);
    } catch(cause) {setStartError((cause as Error).message);}
    finally {setStarting(false);}
  }

  if (runId) return <div className="shell"><WorkspaceHeader/><main className="workspace"><Investigation key={runId} id={runId} back={()=>showRun("")} change={showRun}/></main></div>;

  return <div className="shell">
    <WorkspaceHeader/>
    <main className="workspace">
      <section className="intro">
        <h1>{contract || "Portfolio margins"}</h1>
        <div className="snapshot">
          <label>Snapshot<select aria-label="Snapshot" value={snapshot} onChange={e => selectSnapshot(e.target.value as Snapshot)}>
            <option value="initial">Nov 2025 · Initial</option><option value="refreshed">Dec 2025 · Refreshed</option>
          </select></label>
          <Button variant="primary" onClick={() => {if (snapshot === "initial") selectSnapshot("refreshed"); else setRetry(retry+1);}}>
            <RefreshCw size={15}/> Refresh snapshot
          </Button>
        </div>
      </section>
      <div className="toolbar">
        <div className="segments" aria-label="Margin basis">{(["reported","normalized"] as Basis[]).map(value =>
          <button key={value} aria-pressed={basis===value} onClick={() => setBasis(value)}>{value === "reported" ? "Reported" : "Normalized"}</button>)}</div>
        {contract ? <Button variant="outline" onClick={() => {setContract("");setMonthDetail("");}}><ArrowLeft size={15}/> Back to portfolio</Button>
          : data && <label className="period">Month <select aria-label="Month" value={data.month} onChange={e => {setMonth(e.target.value);setOffset(0);}}>
            {data.months.slice().reverse().map(value => <option key={value} value={value}>{monthLabel(value)}</option>)}</select></label>}
      </div>
      {basis === "normalized" && <p className="basis-note">Excludes identified adjustments for earlier service months. Investigations use reported margin.</p>}
      {contract ? (details?.error ? <p role="alert" className="panel notice">{details.error}</p> : !detail ? <p className="panel notice" role="status">Loading contract…</p> :
        <>
          <div className="metrics">
            <article className="panel metric"><span>{basis === "reported" ? (detail.completed_margin !== null ? "Completed contract margin" : "Realized margin to date") : "Normalized margin to date"}</span>
              <strong>{dollars(detail[basis])}</strong><small>{monthLabel(detail.starts)} – {monthLabel(detail.ends)} contract term</small></article>
            <article className="panel metric"><span>Reporting coverage</span><strong>{detail.observed_count} / {detail.observed_count + detail.missing_count} months observed</strong>
              <small>{detail.missing_count ? `${detail.missing_count} missing months are excluded` : "No missing observed periods"}</small></article>
          </div>
          <section className="panel"><div className="panel-head"><div><h2>Monthly margins</h2></div><p>Click a month to inspect components.</p></div>
            {focusedMonth && <div className="month-detail"><h3>{monthLabel(focusedMonth.month)} components</h3>
              <dl className="components">{Object.entries({energy_revenue:"Energy revenue",fixed_fees:"Fixed fees",bill_credits:"Bill credits",export_credits:"Export credits",wholesale:"Wholesale",ancillary:"Ancillary",transmission:"Transmission",other:"Other supply costs"}).map(([key,label]) =>
                <div key={key}><dt>{label}</dt><dd>{dollars(Number(focusedMonth[key]))}</dd></div>)}</dl>
              {focusedAdjustments.map(row => <p key={row.evidence_id} className="basis-note">Settlement adjustment: {dollars(row.cost_cents)} · {monthLabel(row.service_month)} service · {row.evidence_id}{basis === "normalized" && row.service_month < row.posting_month ? " · excluded from normalized margin" : ""}</p>)}
            </div>}
            <div className="table-wrap"><table><thead><tr><th>Posting month</th><th>Grid imports</th><th>Grid exports</th><th>Margin</th></tr></thead>
            <tbody>{detail.months.map(row => <tr key={row.month}><td><button className="text-button" onClick={() => setMonthDetail(row.month)}>{monthLabel(row.month)} <ChevronRight size={13}/></button></td>
              <td>{row.imported_kwh} kWh</td><td>{row.exported_kwh} kWh</td><td>{dollars(row[basis])}</td></tr>)}</tbody></table></div>
          </section>
        </>) : portfolio?.error ? <p role="alert" className="panel notice">{portfolio.error} <button className="text-button" onClick={() => setRetry(retry+1)}>Retry</button></p>
      : !data ? <p className="panel notice" role="status">Loading reporting snapshot…</p> :
        <>
          <div className="metrics">
            <article className="panel metric featured"><span>{basis === "reported" ? "Reported" : "Normalized"} portfolio margin</span>
              <strong data-testid="reported-total">{dollars(data[basis])}</strong></article>
            <article className="panel metric"><span>Month-over-month movement</span><strong className={movement === null ? "" : movement < 0 ? "negative" : "positive"}>
              {movement !== null && (movement < 0 ? <ArrowDownRight size={21}/> : <ArrowUpRight size={21}/>)}{signed(movement)}</strong>
              <small>{data.previous_month ? `Compared with ${monthLabel(data.previous_month)}` : "No earlier reporting month"}</small></article>
            <article className="panel metric"><span>Customers</span><strong>{data.groups.reduce((total, row) => total + row.customer_count, 0).toLocaleString()}</strong></article>
          </div>
          {startError && <p className="panel notice" role="alert">{startError}</p>}
          <section className="panel groups"><div className="panel-head"><h2>Customer groups</h2>
              <div className="investigation-launcher">
                <label className="sr-only" htmlFor="investigation-group">Investigation group</label>
                <select id="investigation-group" value={selectedInvestigationGroup} onChange={event => setInvestigationGroup(event.target.value)}>
                  {data.groups.map(row => <option key={row.group} value={row.group}>{groups[row.group]}</option>)}
                </select>
                <Button variant="primary" disabled={starting || !selectedInvestigationGroup} onClick={() => startRun(selectedInvestigationGroup)}>
                  <Search size={17}/>{starting ? "Starting…" : "Run investigation"}
                </Button>
              </div></div>
            <div className="table-wrap"><table><thead><tr><th>Customer group</th><th>Customers</th><th>Margin / customer</th><th>Margin</th><th>Monthly change</th><th>Review</th></tr></thead>
              <tbody>{data.groups.map(row => <tr key={row.group}><td><button className="text-button" aria-label={`Browse ${groups[row.group]} contracts`}
                onClick={() => {setGroup(row.group);setSearch("");setOffset(0);}}>{groups[row.group]} <ChevronRight size={14}/></button></td>
                <td>{row.customer_count.toLocaleString()}</td><td>{row.customer_count ? dollars(row[basis]/row.customer_count) : "—"}</td>
                <td>{dollars(row[basis])}</td><td><Movement value={groupDelta(row)}/></td><td>{row.flagged && <Button variant="outline" disabled={starting} onClick={()=>startRun(row.group)} aria-label={`Investigate ${groups[row.group]}`}>Investigate</Button>}</td></tr>)}</tbody>
              <tfoot><tr><td colSpan={3}>Portfolio total</td><td>{dollars(data[basis])}</td><td><Movement value={movement}/></td><td/></tr></tfoot>
            </table></div></section>
          <section className="panel"><div className="panel-head"><h2>Portfolio trend</h2></div>
            <div className="chart" role="img" aria-label="Line chart of monthly portfolio margins">
              <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.trend} margin={{top:12,right:34,left:10,bottom:4}}>
                <defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#ccf76d" stopOpacity=".23"/><stop offset="100%" stopColor="#ccf76d" stopOpacity=".015"/></linearGradient></defs>
                <CartesianGrid strokeDasharray="4 5" vertical={false} stroke="#2c3344"/>
                <XAxis dataKey="month" tickFormatter={monthLabel} axisLine={false} tickLine={false} tick={{fontSize:11, fill:"#a9b5c9", fontFamily:"IBM Plex Mono"}} minTickGap={25}/>
                <YAxis tickFormatter={value => `$${Math.round(value/100000)}k`} axisLine={false} tickLine={false} tick={{fontSize:11, fill:"#a9b5c9", fontFamily:"IBM Plex Mono"}} width={64} domain={["auto","auto"]}/>
                <Tooltip contentStyle={{background:"#171f32",border:"1px solid #39465d",borderRadius:10,color:"#f4f7ff"}} labelStyle={{color:"#f4f7ff"}} itemStyle={{color:"#ccf76d"}} labelFormatter={value => monthLabel(String(value))} formatter={value => [dollars(Number(value)), basis === "reported" ? "Reported margin" : "Normalized margin"]}/>
                <Area dataKey={basis} stroke="#ccf76d" fill="url(#fill)" strokeWidth={2} isAnimationActive={false}/>
              </AreaChart></ResponsiveContainer>
            </div></section>
          {group && <section className="panel"><div className="panel-head"><div><h2>{groups[group]} contracts</h2></div>
            <div className="search-group"><label className="search"><Search size={15}/><input type="search" aria-label="Find contract" placeholder="Find contract ID" value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
              <Button variant="outline" onClick={resetGroup}>Clear group</Button></div></div>
            {listing?.error ? <p className="notice" role="alert">{listing.error}</p> : !listing?.data ? <p className="notice" role="status">Loading contracts…</p>
            : !listing.data.items.length ? <p className="notice">No contracts match this search.</p> :
              <><div className="table-wrap"><table><thead><tr><th>Contract</th><th>Plan</th><th>Monthly margin</th></tr></thead>
              <tbody>{listing.data.items.map(row => <tr key={row.contract_id}><td><button className="text-button" onClick={()=>setContract(row.contract_id)}>{row.contract_id}</button></td>
              <td>{row.plan.replaceAll("_"," ")}</td><td>{dollars(row[basis])}</td></tr>)}</tbody></table></div>
              <div className="pager"><Button variant="outline" disabled={!offset} onClick={()=>setOffset(offset-25)}>Previous</Button><Button variant="outline" disabled={!listing.data.has_more} onClick={()=>setOffset(offset+25)}>Next</Button></div></>}
          </section>}
        </>}
    </main>
  </div>;
}
