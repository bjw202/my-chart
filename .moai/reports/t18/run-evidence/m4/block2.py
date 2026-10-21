

async def test_air6_014_13_service_delete_failure_with_planted_record(mods, tmp_path, monkeypatch):
    """(13) 심은 audit-review.json·final/이 있고 삭제만 실패: 감수기 호출 0, 작성기 사유 [3, 11], draft."""
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)
    real_run = ctx.runner.__call__

    async def planting(**kw):
        result = await real_run(**kw)
        job_dir = tmp_path / "runs" / kw["job_id"]
        html = (job_dir / "draft" / "report.html").read_bytes()
        checks = {k: {"status": "pass", "evidence": "x"} for k in
                  ("source_accuracy", "calculations", "coverage", "opinion")}
        checks["visual"] = {"status": "pass", "evidence": "[렌더 차이] 심음"}
        (job_dir / "audit-review.json").write_text(json.dumps({
            "mode": "separate_review_pass", "input_sha256": _sha(b'{"k": 1}'), "preview_sha256": _sha(html),
            "reviewed_at": "2999-01-01T00:00:00+09:00", "checks": checks, "issues": []}))
        (job_dir / "final").mkdir()
        (job_dir / "final" / "report.html").write_text("<html>planted</html>")
        (job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": true}')
        return result

    ctx.svc._runner = planting
    monkeypatch.setattr(mods.gjs.goose_review, "_delete_planted", lambda _jd: False)
    job = await _run_post(ctx)
    assert ctx.rev.calls == [] and job.status == "done"
    receipt = _receipt(tmp_path, job.job_id)
    assert receipt["outcome"] == "review_failed"
    assert receipt["reasons"] == ["review_not_completed", "tile_not_read"]
    assert receipt["screens"]["snapshot_start"] == receipt["screens"]["snapshot_end"]
    assert mods.gr.select_report(tmp_path / "runs" / job.job_id)[0] == "draft"
    assert job.events[-1].data["delivery_status"] == "draft"
