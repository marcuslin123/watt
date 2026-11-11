"use client";

import { Button } from "./ui/button";

import Decisions, { ReviewForm } from "./decisions";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, ChevronDown, CircleAlert, FileCheck2, LoaderCircle, RotateCcw, Square } from "lucide-react";

type Event = { id: number; kind: string; text: string };
type Evidence = { tool:string; id:string; title:string; document?:{body:string; section:string; effective_from:string; published_on:string; synthetic:boolean; source_url?:string}; record?:{provenance:string;source:string;record_date:string;contract_id:string;note:string}; [key:string]: unknown };
type Finding = {key:string; status:string; title:string; detail:string; amount_cents:number|null; reviewed_contracts?:string[]; evidence:Evidence[]};
type Run = { id:string; scope:{snapshot:string; month:string; group:string}; parent_id:string|null;
  status:string; findings:Finding[]; message:string|null; events:Event[] };
const active = new Set(["queued","running"]);
const runLabels: Record<string, string> = {
  queued: "Waiting to start",
  running: "Investigating",
  completed: "Complete",
  partial: "Partial results",
  failed: "Run failed",
  cancelled: "Cancelled",
  interrupted: "Interrupted",
};
const cents = (amount: number) => new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(amount/100);
const progressMessages: Record<string, string> = {
  queued: "Watt will start when the worker is available.",
  running: "Connecting to Codex",
  verified: "Planning which checks to run",
  checked: "Reviewing the evidence",
};

function InvestigationProgress({events}: {events:Event[]}) {
  const pending: Event[] = [];
  const completed: Event[] = [];
  for (const event of events) {
    if (event.kind === "tool") pending.push(event);
    if (event.kind === "checked") {
      completed.push(event);
      const index = pending.findIndex(step => step.text === event.text.replace(/ · complete$/, ""));
      if (index >= 0) pending.splice(index, 1);
    }
  }

  const phase = events.at(-1)?.kind;
  const heading = !phase ? "Loading investigation" : phase === "queued" ? "Waiting to start" :
    "Investigation in progress";
  const current = phase && (pending.at(-1)?.text ?? progressMessages[phase] ?? "Loading the run outcome");

  return <section className="panel investigation-progress investigation-stage" aria-labelledby="investigation-progress-title">
    <div className="progress-current" role="status">
      <span className="progress-icon"><LoaderCircle size={24} aria-hidden="true"/></span>
      <div>
        <h2 id="investigation-progress-title">{heading}</h2>
        {current && <p className="progress-step" key={current}>{current}</p>}
      </div>
    </div>
    {(completed.length > 0 || pending.length > 1) && <ul className="progress-checks" aria-label="Investigation checks">
      {completed.map(event => <li key={event.id}>
        <Check size={18} aria-hidden="true"/><span className="sr-only">Completed </span>{event.text.replace(/ · complete$/, "")}
      </li>)}
      {pending.slice(0, -1).map(event => <li key={event.id}>
        <LoaderCircle size={18} aria-hidden="true"/><span className="sr-only">In progress </span>{event.text}
      </li>)}
    </ul>}
  </section>;
}

export default function Investigation({id, back, change}: {id:string; back:()=>void; change:(id:string)=>void}) {
  const [run,setRun] = useState<Run>();
  const [events,setEvents] = useState<Event[]>([]);
  const [selected,setSelected] = useState<string>("");
  const [error,setError] = useState("");
  const [reloading,setReloading] = useState(0);
  const [pendingAction, setPendingAction] = useState(false);
  useEffect(() => {
    let stopped = false;
    let source: EventSource | undefined;
    async function load() {
      const response = await fetch("/api/investigations/"+id, {cache:"no-store"});
      if (!response.ok) throw new Error("Could not load this investigation");
      const value = await response.json() as Run;
      if (stopped) return;
      setRun(value);setEvents(value.events);setError("");
      if (!active.has(value.status)) return;
      source = new EventSource("/api/investigations/"+id+"/stream?after="+(value.events.at(-1)?.id ?? 0));
      source.onmessage = (message) => {
        const row = JSON.parse(message.data) as Event;
        setEvents(all => all.some(item => item.id===row.id) ? all : [...all,row]);
      };
      source.addEventListener("terminal", () => {
        source?.close(); setReloading(count=>count+1);
      });
    }
    load().catch((cause) => {if(!stopped) setError(cause.message);});
    return () => {stopped=true;source?.close();};
  },[id,reloading]);

  async function action(name:"cancel"|"rerun") {
    setPendingAction(true);
    setError("");
    try {
      const response=await fetch("/api/investigations/"+id+"/"+name,{method:"POST"});
      if(!response.ok) throw new Error("Could not "+name+" this investigation");
      if(name==="rerun") change((await response.json()).id);
      else setReloading(count=>count+1);
    } catch(cause) {setError((cause as Error).message);}
    finally {setPendingAction(false);}
  }

  const status = run?.status === "queued" && events.some(item => item.kind === "running")
    ? "running"
    : run?.status;
  const inProgress = !run || active.has(run.status);

  const bridge = run?.findings.find(finding => finding.key === "bridge");
  const context = run?.findings.find(finding => finding.key === "context");
  const drivers = run?.findings.filter(finding => finding.key !== "bridge" && finding.key !== "context") ?? [];

  const renderEvidence = (finding: Finding) => <>
    <div className="evidence-buttons">{finding.evidence.map(item=><Button variant="outline"
      aria-expanded={selected===finding.key+item.id} key={item.id} onClick={()=>setSelected(selected===finding.key+item.id?"":finding.key+item.id)}>
      <FileCheck2 size={14}/>{item.title}</Button>)}</div>
    {finding.evidence.filter(item=>selected===finding.key+item.id).map(item=><div className="evidence-detail" key={item.id}>
      <p className="eyebrow">SOURCE · {item.id}</p>
      {item.record ? <><p>{item.record.note}</p><small>{item.record.provenance} · {item.record.contract_id} · {item.record.record_date}</small></>
        : item.document ? <><p>{item.document.body}</p><small>{item.document.section} · effective {item.document.effective_from} · published {item.document.published_on} · {item.document.synthetic?"synthetic record":"public source"}</small>{item.document.source_url?.startsWith("https://") && <p><a className="text-button" href={item.document.source_url} target="_blank" rel="noreferrer">Open public source</a></p>}</>
        : <pre>{JSON.stringify(Object.fromEntries(Object.entries(item).filter(([key])=>!["id","title","tool"].includes(key))),null,2)}</pre>}
    </div>)}
  </>;

  const renderFinding = (finding: Finding) => <div key={finding.key} className="finding">
    <div className="finding-top"><h3>{finding.title}</h3>
      {finding.amount_cents!==null && <strong>{cents(finding.amount_cents)}</strong>}</div>
    {finding.status === "unresolved" && <span className="finding-review">Needs review</span>}
    <p>{finding.detail}</p>
    {renderEvidence(finding)}
    {finding.key==="usage" && run && ["completed","partial"].includes(run.status) && <ReviewForm id={run.id} revise={change}
      contracts={((finding.evidence.find(item=>item.id==="usage-drops")?.sample as string[]|undefined) ?? [])
        .filter(contract=>!finding.reviewed_contracts?.includes(contract))}/>}
  </div>;

  return <section className="investigation">
    <Button variant="outline" onClick={back}><ArrowLeft size={15}/> Back to portfolio</Button>
    <div className="intro"><div><h1>Margin investigation</h1>
      {run && <div className="lede run-meta">
        <span>{({solar:"Solar",high_winter:"High winter usage",low_winter:"Low winter usage"} as Record<string,string>)[run.scope.group] ?? run.scope.group} · {new Intl.DateTimeFormat("en-US", {month:"short",year:"numeric",timeZone:"UTC"}).format(new Date(run.scope.month))}</span>
        {status && <span className="run-state" data-state={status} data-testid="run-status" role="status">{runLabels[status] ?? status}</span>}
      </div>}</div>
      {run && (inProgress ? <Button variant="outline" disabled={pendingAction} onClick={()=>action("cancel")}>
        <Square size={15} aria-hidden="true"/>{pendingAction ? "Cancelling…" : "Cancel run"}
      </Button> : <Button variant="outline" disabled={pendingAction} onClick={()=>action("rerun")}>
        <RotateCcw size={15} aria-hidden="true"/>{pendingAction ? "Starting…" : "Run again"}
      </Button>)}</div>
    {error && <p role="alert" className="panel notice">{error}</p>}
    {inProgress && (!error || run) && <InvestigationProgress events={events}/>}
    {run && !inProgress && <article className="panel investigation-report investigation-stage" aria-label="Investigation report">
      {run.message && <p className="notice report-status" role="status">{run.message}</p>}
      {run.parent_id && <div className="report-section"><Button variant="outline" onClick={()=>change(run.parent_id!)}>Open parent run</Button></div>}
      {bridge && <section className="report-section report-lead" aria-label="What changed">
        <h2>What changed</h2>
        {renderFinding(bridge)}
      </section>}
      {run.findings.length > 0 ? <>
        <section className="report-section" aria-label="Margin breakdown">
          <h2>Margin breakdown</h2>
          {drivers.length > 0 ? drivers.map(renderFinding) : <p className="report-note">No verified drivers were identified for this period.</p>}
          {context && <details className="report-disclosure">
            <summary>Public market and weather context <ChevronDown size={16} aria-hidden="true"/></summary>
            <p className="report-note">{context.detail}</p>
            {renderEvidence(context)}
          </details>}
        </section>
        {["completed","partial"].includes(run.status) && <section className="report-section" aria-label="Next steps">
          <h2>Next steps</h2>
          <Decisions id={run.id}/>
        </section>}
      </> : <p className="notice"><CircleAlert size={15}/> No verified findings published yet.</p>}
      {events.length > 0 && <details className="report-disclosure run-log">
        <summary>Investigation activity <ChevronDown size={16} aria-hidden="true"/></summary>
        <ol aria-label="Investigation activity">{events.map(item=><li key={item.id}><span>{item.kind}</span>{item.text}</li>)}</ol>
      </details>}
    </article>}
  </section>;
}
