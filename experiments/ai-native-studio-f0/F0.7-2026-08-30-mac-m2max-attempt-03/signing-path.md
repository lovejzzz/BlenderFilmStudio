# F0.7 macOS signing and notarization path

Snapshot: 2026-08-30. This is an implementation boundary for a future release,
not evidence that the F0.7 research package is signed or publicly distributable.

## Observed research-package state

- The exact F0 product executable is linker-signed ad hoc. `codesign` reports
  `Signature=adhoc`, no team identifier, and `spctl --assess` rejects the app.
- F0.7 intentionally creates an unsigned research DMG. It must retain the
  Gatekeeper rejection as evidence and must not bypass Gatekeeper.
- The installed official `/Applications/Blender.app` is a separate notarized
  Developer ID app and is a negative-control asset, not a signing template.

## Future public-release sequence

1. Enroll the legal release owner in the Apple Developer Program and create a
   Developer ID Application certificate. Apple identifies that certificate as
   the credential for Mac software distributed outside the Mac App Store.
2. Inventory every nested Mach-O, framework, dylib, helper and app extension.
   Sign nested code from the inside out, then sign the outer app with hardened
   runtime, secure timestamp and the release entitlements. Placeholder form:

   ```sh
   /usr/bin/codesign --force --options runtime --timestamp \
     --sign "Developer ID Application: <LEGAL NAME> (<TEAM_ID>)" \
     "<INNER_CODE_OR_OUTER_APP>"
   /usr/bin/codesign --verify --deep --strict --verbose=4 "<SIGNED_APP>"
   ```

3. Build the final DMG from the verified signed app. Store notarization
   credentials in the macOS Keychain under a release-only profile; never pass
   secrets on a logged command line or commit them:

   ```sh
   /usr/bin/xcrun notarytool submit "<SIGNED_DMG>" \
     --keychain-profile "<RELEASE_KEYCHAIN_PROFILE>" --wait
   /usr/bin/xcrun stapler staple "<SIGNED_DMG>"
   /usr/bin/xcrun stapler validate "<SIGNED_DMG>"
   /usr/sbin/spctl --assess --type open --context context:primary-signature \
     --verbose=4 "<SIGNED_DMG>"
   ```

4. Retain the notary submission identifier and log, certificate fingerprint,
   entitlements, signed app/DMG hashes, Gatekeeper assessment and stapled-ticket
   validation in release evidence. Never retain a private key or account secret.

Apple states that current notarization uses `notarytool`, that directly
distributed software should use Developer ID with hardened runtime and secure
timestamp, and that a successful submission produces a ticket that can be
stapled. Apple lists the Developer Program at USD 99 per membership year (or
local currency); no separate per-submission notarization fee is published in
the cited documentation. Labor, legal review, CI and hardware cost remain
unmeasured and must not be reported as zero.

## Credential boundary

- Outside Git: Developer ID private key, certificate export, Apple Account,
  app-specific password, App Store Connect API key, issuer ID and Keychain
  profile.
- Allowed in Git: public certificate fingerprint, team ID after a release owner
  approves disclosure, entitlements, commands with placeholders, notary result
  IDs/logs after secret redaction, artifact hashes and cost basis.
- CI must receive short-lived or repository-scoped secrets from its secret
  store. A research agent may document the flow but may not select or use a
  signing identity without explicit release authority.

## Official sources

- [Apple: Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Apple: Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates)
- [Apple: Developer Program membership details](https://developer.apple.com/programs/whats-included/)
- [Apple Platform Security: Gatekeeper and runtime protection](https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web)

