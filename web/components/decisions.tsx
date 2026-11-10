"use client";

import { FormEvent, useState } from "react";

const dollars = (amount: number) => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"}).format(amount / 100);
const percent = (value: number) => (value / 100).toFixed(2) + "%";
type Scenario = { baseline_cents:number; offer_cents:number; incremental_cents:number; break_even_offer_bps:number|null; required_uplift_bps:number|null; usage_unresolved:boolean };
type Answer = { message:string; rows:{title:string; status:string; detail:string; amount_cents:number|null; sources:string[]}[] };

async function post<T>(runId:string, route:string, body:object): Promise<T> {
  const response = await fetch(`/api/investigations/${runId}/${route}`, {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check the supplied values and try again.");
  return data;
}

export function ReviewForm({id, contracts, revise}: {id:string; contracts:string[]; revise:(id:string)=>void}) {
  const [message,setMessage] = useState("");
  const [busy,setBusy] = useState(false);
  if (!contracts.length) return null;
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");setBusy(true);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try { revise((await post<{id:string}>(id,"review",values)).id); }
    catch(error) {setMessage((error as Error).message);}
    finally {setBusy(false);}
  }
  return <details className="review-form">
    <summary>Attach analyst evidence</summary>
    <p>Use a dated record for one contract in this finding. Watt preserves the original run and records your source.</p>
    <form onSubmit={submit}>
      <label>Contract<select name="contract_id" required>{contracts.map(contract=><option key={contract}>{contract}</option>)}</select></label>
      <label>Record date<input type="date" name="record_date" required/></label>
      <label>Source<input name="source" required minLength={4} maxLength={120} placeholder="Service record or meter review"/></label>
      <label className="wide">What does the record show?<textarea name="note" required minLength={12} maxLength={600} rows={3}/></label>
      <button className="button primary" disabled={busy}>Save evidence as revision</button>
    </form>
    {message && <p role="alert">{message}</p>}
  </details>;
}

export default function Decisions({id}: {id:string}) {
  const [answer,setAnswer] = useState<Answer>();
  const [result,setResult] = useState<Scenario>();
  const [questionError,setQuestionError] = useState("");
  const [scenarioError,setScenarioError] = useState("");
  const [asking,setAsking] = useState(false);
  const [calculating,setCalculating] = useState(false);
  async function ask(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();setAsking(true);setQuestionError("");setAnswer(undefined);
    try {setAnswer(await post<Answer>(id,"follow-up",Object.fromEntries(new FormData(event.currentTarget))));}
    catch(error) {setQuestionError((error as Error).message);}
    finally {setAsking(false);}
  }
  async function compare(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();setCalculating(true);setScenarioError("");setResult(undefined);
    const form = new FormData(event.currentTarget);
    const number = (name:string, scale=1) => Math.round(Number(form.get(name))*scale);
    try {
      setResult(await post<Scenario>(id,"scenario",{
        customers:number("customers"), contribution_cents:number("contribution",100),
        baseline_bps:number("baseline",100), offer_bps:number("offer",100),
        outreach_cents:number("outreach",100), incentive_cents:number("incentive",100)
      }));
    } catch(error) {setScenarioError((error as Error).message);}
    finally {setCalculating(false);}
  }
  return <>
    <section className="panel decision" aria-label="Investigation follow-up">
      <p className="eyebrow">SAVED FINDINGS</p><h2>Ask a follow-up</h2>
      <form className="question-form" onSubmit={ask}>
        <label>Question<input name="question" required minLength={3} maxLength={300} placeholder="Which drivers explain the margin decline?"/></label>
        <button className="button primary" disabled={asking}>Ask Watt</button>
      </form>
      {questionError && <p role="alert">{questionError}</p>}
      {answer && <div aria-live="polite"><p>{answer.message}</p>
        {answer.rows.length>0 && <div className="table-wrap"><table><thead><tr><th>Finding</th><th>Amount</th><th>Status</th></tr></thead>
          <tbody>{answer.rows.map(row=><tr key={row.title}><td>{row.title}<small>{row.detail} · {row.sources.join(", ")}</small></td>
            <td>{row.amount_cents===null?"—":dollars(row.amount_cents)}</td><td>{row.status}</td></tr>)}</tbody></table></div>}</div>}
    </section>
    <section className="panel decision" aria-label="Retention scenario">
      <p className="eyebrow">DECISION SUPPORT / 12 MONTHS</p><h2>Compare a retention offer</h2>
      <p>Illustrative assumptions, not a forecast. Future contribution is conditional on staying and is entered separately from historical margin.</p>
      <form className="scenario-form" onSubmit={compare}>
        <label>Customers<input name="customers" type="number" min={1} max={10000} defaultValue={60} required/></label>
        <label>Contribution if retained ($)<input name="contribution" type="number" step=".01" min={-100000} max={100000} defaultValue={300} required/></label>
        <label>Stay probability without offer (%)<input name="baseline" type="number" step=".01" min={0} max={100} defaultValue={70} required/></label>
        <label>Stay probability with offer (%)<input name="offer" type="number" step=".01" min={0} max={100} defaultValue={80} required/></label>
        <label>Outreach per customer ($)<input name="outreach" type="number" step=".01" min={0} max={100000} defaultValue={3} required/></label>
        <label>Incentive per retained customer ($)<input name="incentive" type="number" step=".01" min={0} max={100000} defaultValue={25} required/></label>
        <button className="button primary" disabled={calculating}>Compare scenarios</button>
      </form>
      {scenarioError && <p role="alert">{scenarioError}</p>}
      {result && <div className="scenario-result" aria-live="polite">
        <dl className="components">
          <div><dt>No offer</dt><dd>{dollars(result.baseline_cents)}</dd></div>
          <div><dt>With offer</dt><dd>{dollars(result.offer_cents)}</dd></div>
          <div><dt>Incremental contribution</dt><dd data-testid="scenario-incremental">{dollars(result.incremental_cents)}</dd></div>
        </dl>
        <p>{result.break_even_offer_bps===null ? "No feasible break-even at or above the baseline probability." :
          `Break-even at ${percent(result.break_even_offer_bps)} stay probability (${((result.required_uplift_bps ?? 0)/100).toFixed(2)} percentage points above baseline).`}</p>
        {result.usage_unresolved && <p className="flag">Usage cause remains unresolved. Confirm assumptions before using this comparison for a decision.</p>}
      </div>}
    </section>
  </>;
}
