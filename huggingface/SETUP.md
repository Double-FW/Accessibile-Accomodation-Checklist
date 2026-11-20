# Weekly accommodation dataset sync

Destination: https://huggingface.co/datasets/GarethFW/Designing_Accessible_Accommodation

1. Open [Actions variables](https://github.com/Double-FW/Accessibile-Accomodation-Checklist/settings/variables/actions). Add or edit the ordinary variable `HF_DATASET_ID` to `GarethFW/Designing_Accessible_Accommodation`. It is a dataset name, not the token or a full URL.
2. Open https://huggingface.co/settings/tokens and create a Fine-grained/Custom token. Select only `GarethFW/Designing_Accessible_Accommodation` under repository permissions and grant read and write access. Leave unrelated permissions unticked. Copy the generated `hf_` token privately.
3. Open [Actions secrets](https://github.com/Double-FW/Accessibile-Accomodation-Checklist/settings/secrets/actions). Add or update `HF_TOKEN` with the generated token, using an underscore in the name. Do not paste the dataset name into this secret or share the token in chat.
4. Open [the workflow](https://github.com/Double-FW/Accessibile-Accomodation-Checklist/actions/workflows/huggingface-sync.yml), choose Run workflow on main and open the new run. Confirm the publishing step succeeds and inspect the destination Files tab before reporting the sync complete.

Schedule: Monday 10:07 UTC (10:07 UK winter, 11:07 UK summer). GitHub can delay scheduled runs or disable schedules in inactive public repositories. Manual runs remain available.

The source must remain public; the target must already exist. The publisher authenticates its source check with GitHub’s automatically supplied read-only token. You do not need a separate GitHub token. HF_TOKEN is supplied only to the publishing step. No-change runs do not create dataset commits. Only eight named managed files are written atomically against the observed target revision; unrelated files and target visibility are preserved.

The export provides 32 checklist item records and five complete guidance documents, plus the original complete checklist as `checklist.md`. Item records preserve their section, P/N/C tags and full shared scope, authority, safety, recording and source context. The complete checklist and item stream are alternative representations, not independent evidence. No external source bodies, personal records, invented answers, completed inspections or test/audit report files are published. Source hashes and provenance describe origin, not product effectiveness or legal validation.

New source files require review and an explicit export-configuration update. Licence changes, a wrong target, missing/dirty approved sources or failed checks stop publication.

For local checks, install `huggingface/requirements.txt`, run `python scripts/export_huggingface.py --check-only` and `python -m unittest discover -s tests -v`. Build a preview with `python scripts/export_huggingface.py --output /tmp/accommodation-preview --dataset-id GarethFW/Designing_Accessible_Accommodation`. Tests use a simulated destination, not real credentials.
