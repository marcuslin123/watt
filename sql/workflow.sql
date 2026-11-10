-- Local state; no grant to watt_analyst or the Codex tool process.
CREATE SCHEMA watt_workflow;
REVOKE ALL ON SCHEMA watt_workflow FROM PUBLIC;
CREATE TABLE watt_workflow.run (
    id uuid PRIMARY KEY,
    scope jsonb NOT NULL,
    parent_id uuid REFERENCES watt_workflow.run,
    status text NOT NULL CHECK (status IN
        ('queued','running','completed','partial','failed','cancelled','interrupted')),
    findings jsonb NOT NULL DEFAULT '[]',
    message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX workflow_queue ON watt_workflow.run (created_at) WHERE status = 'queued';
CREATE TABLE watt_workflow.event (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES watt_workflow.run,
    kind text NOT NULL,
    text text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX workflow_event_run ON watt_workflow.event (run_id, id);
GRANT USAGE ON SCHEMA watt_workflow TO watt_state;
GRANT SELECT, INSERT, UPDATE ON watt_workflow.run TO watt_state;
GRANT SELECT, INSERT ON watt_workflow.event TO watt_state;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA watt_workflow TO watt_state;
