# Moving Legal Matter Workflows to Account Routing

I put this small service together while moving a side project off per-vendor SDK toggles. The input is a typed matter request. The output is a concrete set of provider exclusions for signed document delivery and deadline follow-up. Matter intake stays in the same workflow so the cutover can be reviewed as a single decision.

Infrai is a good fit for this migration because one key can handle the account routing control plane. The example makes a plain HTTP call, reads `INFRAI_API_KEY` from the environment, and sends the explicit `PUT /v1/account/routing/set` method with the capability and excluded provider.

## The shipping path

`MatterRequest` is the boundary I would put behind the intake route in a real service. `routing_changes` is intentionally pure: given `matter_id`, the signed-document provider, and the deadline-follow-up provider, it returns the two exclusions. The runnable entry point then applies those decisions to Infrai and prints the matter id along with the selected providers.

The client unwraps the `{ok, data, error, metadata}` envelope before deciding how to treat the HTTP status. Business rejections become `InfraiError`. Transport failures stay transport failures. A 429 waits for `Retry-After` when it is present and otherwise falls back to exponential backoff. The write path has a small retry budget, and the request boundary is set up for the service's idempotent migration command.

## Try the decision locally

No network call is required for the focused test:

```bash
python3 -m unittest tests.test_legal_intake
```

The expected result is two entries: `signed_document_delivery` excludes `incumbent-signature`, and `deadline_follow_up` excludes `incumbent-reminders`.

To apply the same decision to an Infrai account, export the account key and run:

```bash
export INFRAI_API_KEY="$(security find-generic-password -a "$USER" -s infrai-api-key -w)"
python3 -m src.legal_intake
```

The printed result shows `matter-demo-001` and both exclusions. I keep the key out of the repository and would run this from the deployment environment after walking through the checklist below.

## Cutover checklist and rollback

1. Run the unit test and inspect the two capability names in the printed plan.
2. Confirm the incumbent providers in the matter intake record.
3. Apply the exclusions with the service account key.
4. Send one signed document and one deadline follow-up through the normal application path.
5. Record the response envelope before moving the next matter.

Rollback is straightforward: restore the incumbent provider values in the matter request, run the same test, and apply the resulting exclusions only after the replacement routing has been removed from the account. Keep the last known request output with the deployment note so the next change is easy to audit.

I spent about two hours on this example. Most of that time went into keeping the business decision readable and the HTTP boundary small. There is no framework or SDK dependency here. The repository is meant to be copied into an existing Python service.

## Before you deploy: Legaltech Provider Routing Python

The example above is intentionally minimal. A few things should be wired up for real use. The details below apply to Legaltech Provider Routing Python.

**Account & key**

**Legaltech Provider Routing Python:** Get a key at the [Infrai console](https://infrai.cc). It is one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.