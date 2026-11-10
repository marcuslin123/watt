"use client";

import Decisions, { ReviewForm } from "./decisions";
import { useEffect, useState } from "react";
import { ArrowLeft, CircleAlert, FileCheck2, FlaskConical } from "lucide-react";

type Event = { id: number; kind: string; text: string };
type Evidence = { tool:string; id:string; title:string; document?:{body:string; section:string; effective_from:string; published_on:string; synthetic:boolean; source_url?:string}; record?:{provenance:string;source:string;record_date:string;contract_id:string;note:string}; [key:string]: unknown };
type Finding = {key:string; status:string; title:string; detail:string; amount_cents:number|null; reviewed_contracts?:string[]; evidence:Evidence[]};
type Run = { id:string; scope:{snapshot:string; month:string; group:string}; parent_id:string|null;
  status:string; findings:Finding[]; message:string|null; events:Event[] };
const active = new Set(["queued","running"]);
const cents = (amount: number) => new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(amount/100);

export default function Investigation({id, back, change}: {id:string; back:()=>void; change:(id:string)=>void}) {
  const [run,setRun] = useState<Run>();
  const [events,setEvents] = useState<Event[]>([]);
  const [selected,setSelected] = useState<string>("");
  const [error,setError] = useState("");
  const [reloading,setReloading] = useState(0);
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
    try {
      const response=await fetch("/api/investigations/"+id+"/"+name,{method:"POST"});
      if(!response.ok) throw new Error("Could not "+name+" this investigation");
      if(name==="rerun") change((await response.json()).id);
      else setReloading(count=>count+1);
    } catch(cause) {setError((cause as Error).message);}
  }

  return <section className="investigation">
    <button className="button ghost" onClick={back}><ArrowLeft size={15}/> Back to portfolio</button>
    <div className="intro"><div><p className="eyebrow">WATT / SCOPED INVESTIGATION</p><h1>Margin investigation</h1>
      {run && <p className="lede">{run.scope.group.replaceAll("_"," ")} · {run.scope.month.slice(0,7)} · {run.scope.snapshot} snapshot</p>}</div>
      {run && <div className="snapshot"><span className="synthetic" data-testid="run-status">{run.status}</span>
      {active.has(run.status) ? <button className="button ghost" onClick={()=>action("cancel")}>Cancel run</button>
      : <button className="button ghost" onClick={()=>action("rerun")}>Run again</button>}</div>}</div>
    {error && <p role="alert" className="panel notice">{error}</p>}
    {!run && !error && <p role="status" className="panel notice">Loading investigation…</p>}
    {run && <div className="invest-grid">
      <div>
        {run.message && <p className="panel notice" role="status">{run.message}</p>}
        {run.parent_id && <button className="button ghost revision-link" onClick={()=>change(run.parent_id!)}>Open parent run</button>}
        {run.findings.map(finding=><article key={finding.key} className="panel finding">
          <div className="finding-top"><span className={finding.status==="unresolved"?"flag":"synthetic"}>{finding.status}</span>
            {finding.amount_cents!==null && <strong>{cents(finding.amount_cents)}</strong>}</div>
          <h2>{finding.title}</h2><p>{finding.detail}</p>
          <div className="evidence-buttons">{finding.evidence.map(item=><button className="button ghost"
            aria-expanded={selected===finding.key+item.id} key={item.id} onClick={()=>setSelected(selected===finding.key+item.id?"":finding.key+item.id)}>
            <FileCheck2 size={14}/>{item.title}</button>)}</div>
          {finding.evidence.filter(item=>selected===finding.key+item.id).map(item=><div className="evidence-detail" key={item.id}>
            <p className="eyebrow">SOURCE · {item.id}</p>
            {item.record ? <><p>{item.record.note}</p><small>{item.record.provenance} · {item.record.contract_id} · {item.record.record_date}</small></>
              : item.document ? <><p>{item.document.body}</p><small>{item.document.section} · effective {item.document.effective_from} · published {item.document.published_on} · {item.document.synthetic?"synthetic record":"public source"}</small>{item.document.source_url?.startsWith("https://") && <p><a className="text-button" href={item.document.source_url} target="_blank" rel="noreferrer">Open public source</a></p>}</>
              : <pre>{JSON.stringify(Object.fromEntries(Object.entries(item).filter(([key])=>!["id","title","tool"].includes(key))),null,2)}</pre>}
          </div>)}
          {finding.key==="usage" && ["completed","partial"].includes(run.status) && <ReviewForm id={run.id} revise={change}
            contracts={((finding.evidence.find(item=>item.id==="usage-drops")?.sample as string[]|undefined) ?? [])
              .filter(contract=>!finding.reviewed_contracts?.includes(contract))}/>}
        </article>)}
        {run.findings.length>0 && ["completed","partial"].includes(run.status) && <Decisions id={run.id}/>}
        {!run.findings.length && <p className="panel notice"><CircleAlert size={15}/> No verified findings published yet.</p>}
      </div>
      <aside className="panel run-log"><div className="panel-head"><div><p className="eyebrow">EXECUTION LOG</p><h2>Investigation activity</h2></div><FlaskConical size={18}/></div>
        <ol aria-label="Investigation activity">{events.map(item=><li key={item.id}><span>{item.kind}</span>{item.text}</li>)}</ol>
        <p className="notice">Progress reflects actual tool activity. Model reasoning is not shown.</p>
      </aside>
    </div>}
  </section>;
}
