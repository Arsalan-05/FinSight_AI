export function StatusPill({ ok }: { ok: boolean | null }) {
  return (
    <span
      className={[
        "status-pill",
        ok === true ? "status-pill--ok" : ok === false ? "status-pill--err" : "",
      ].join(" ")}
    >
      <span
        className={[
          "status-dot",
          ok === true ? "status-dot--pulse" : ok === false ? "status-dot--err" : "",
        ].join(" ")}
      />
      {ok === true ? "Connected" : ok === false ? "Offline" : "Checking…"}
    </span>
  );
}
