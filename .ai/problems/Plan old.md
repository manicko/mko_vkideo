# Windows Domain Recovery Runbook: Preventing User Lockout

## 1. Context

When a restored Active Directory becomes available, domain-joined computers immediately begin receiving and applying Group Policy Objects (GPOs) from the domain. These restored GPOs—especially those related to security baselines, account policies, and local group membership—can disrupt access in ways that are difficult to reverse without local administrative credentials.

**Authentication risks after domain restoration:**

- **Password reset**: The domain user's password may be different from what they remember. Cached credentials only match the *old* password.
- **Account lockout**: If the user enters the wrong password against a live domain controller, the account can be locked out. A locked account will not authenticate even with cached credentials if a DC is reachable.
- **Account disable**: A disabled account at the DC is rejected outright. Cached credentials are not consulted when a DC responds.
- **Local Administrators membership removal**: Restricted Groups or "Group Policy Preferences" can strip the domain user from the local Administrators group at computer startup.
- **Built-in Administrator rename**: The "Accounts: Rename administrator account" policy renames the local built-in Administrator (RID 500). If the new name is unknown, recovery becomes harder.
- **Cached credential count set to 0**: The "Interactive logon: Number of previous logons to cache" setting can be set to 0, preventing any cached credential use when the DC is unreachable.

**Key distinction — domain-dependent vs. local-independent access:**

| Aspect | Domain-dependent | Local-independent |
|---|---|---|
| Authentication | DC validates password | Local SAM validates password |
| Account lockout | Enforced by DC | N/A (local accounts follow local lockout policy) |
| Affected by GPO | Yes (rename, disable, group removal) | No (local accounts persist unless overwritten) |
| Works offline | Only with cached credentials | Always (if password is known) |

**Critical property of the built-in Administrator account (RID 500):**
The built-in Administrator account is **exempt from account lockout policies** by default. Even if a GPO enforces an account lockout threshold, the built-in Administrator cannot be locked out. This makes it the most reliable recovery account. However, it can still be renamed by the "Accounts: Rename administrator account" policy.

**Strategy overview:**
Before reconnecting to the restored domain, establish two independent local administrator recovery paths and verify cached credential availability. Use Safe Mode (which does not process domain GPOs) for the first boot after reconnection to verify local access before any policies are applied.

---

## 2. Protect the Computer Before Domain Policies Are Restored

> **Prerequisite**: Log in now using the domain user account with cached credentials. This user has local administrator privileges and can run elevated commands. If the domain user cannot log in, boot to Safe Mode and use the built-in Administrator account (if already enabled) or a Windows PE recovery environment with a password reset utility.

### Step 1: Enable and secure the built-in Administrator account

**What to do:** Enable the built-in Administrator account and set a strong, unique password.

**Why:** The built-in Administrator (RID 500) is always a local account, always retains administrative privileges, and is exempt from account lockout policies. Even after domain GPOs apply, it remains accessible unless explicitly renamed. It also works in Safe Mode by default.

**How:**
```cmd
REM Open an elevated Command Prompt (or PowerShell as Administrator)

net user Administrator "Str0ngP@ssw0rd!2024" /active:yes /expires:never
```

**How to verify:**
```cmd
net user Administrator
```
Confirm the output shows `Account active: Yes`.

**What could go wrong:**
- If the domain GPO later renames this account, the name "Administrator" will no longer exist. **Mitigation**: Also create a secondary local admin account (Step 2) whose name is not governed by the rename GPO.
- If the password is weak or reused elsewhere, it could be compromised. **Mitigation**: Use a long, random password unique to this machine.

---

### Step 2: Create a secondary local administrator account

**What to do:** Create a new local user account, add it to the local Administrators group, and set a strong password.

**Why:** The "Accounts: Rename administrator account" GPO only affects the built-in Administrator (RID 500). A separately created admin account with a different name will not be renamed or affected by this policy. This provides a second recovery path if the built-in account is renamed and its new name is unknown.

**How:**
```cmd
net user RecoveryAdmin "RecoverP@ss!2024" /add /expires:never
net localgroup Administrators RecoveryAdmin /add
```

**How to verify:**
```cmd
net user RecoveryAdmin
net localgroup Administrators
```
Confirm `RecoveryAdmin` appears in the Administrators group listing.

**What could go wrong:**
- A Restricted Groups GPO could remove `RecoveryAdmin` from the Administrators group at the next startup. **Mitigation**: This account is a *backup* for the Safe Mode verification step (Step 5). In Safe Mode, domain GPOs do not apply, so the account retains its membership.
- If this account's password is guessed, it provides admin access. **Mitigation**: Use a strong password; treat it as a recovery credential.

---

### Step 3: Verify domain user cached credentials

**What to do:** Ensure the domain user can log in without a live domain controller. This is done by having the user log in once while the computer is offline (or by logging in now with the DC unreachable).

**Why:** When the domain is restored and GPOs are applied, the domain user's account might be locked, disabled, or have its password changed. If cached credentials exist, the user can still log in using their last-known password when the DC cannot be reached. This is the primary way the user continues to use the computer if the domain account has issues.

**How:**
1. Disconnect the network (unplug Ethernet or disable Wi-Fi).
2. Have the domain user log in with their domain credentials as usual.
3. If login succeeds, cached credentials are now stored.
4. Verify the cache count:

```cmd
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v CachedLogonsCount
```

The default value is `10`. Any value greater than `0` allows cached credential use.

**How to verify:**
- The user successfully logged in while offline.
- `CachedLogonsCount` is greater than `0`.

**What could go wrong:**
- The user does not remember their last password. **Mitigation**: This is unavoidable; the local admin accounts (Steps 1 and 2) provide the independent recovery path.
- A domain GPO may set `CachedLogonsCount` to `0` after reconnection. **Mitigation**: Check this value again after the first normal boot (see Step 6 in Section 3).
- The domain user's password may have been changed at the domain level. **Mitigation**: The user must obtain the new password from the domain administrator. Local admin accounts provide independent access meanwhile.

---

### Step 4: Document current local Administrators group membership

**What to do:** Record the current members of the local Administrators group for before/after comparison.

**Why:** After domain GPOs apply, Restricted Groups policies may alter the membership of the local Administrators group. Having a baseline allows quick identification of what changed and what needs to be restored.

**How:**
```cmd
net localgroup Administrators > C:\temp\admins_before.txt
```

Save this file to external media (USB drive) in case the computer becomes inaccessible.

**How to verify:** Review the file contents to ensure the domain user appears in the list.

**What could go wrong:**
- Forgetting to save the baseline before reconnection. **Mitigation**: This step must be done before any network reconnection.
- The baseline file is lost if the computer is reformatted. **Mitigation**: Store it on external media.

---

### Step 5: Configure Safe Mode boot for first reconnection

**What to do:** Set the computer to boot into Safe Mode on the next startup using `bcdedit`.

**Why:** In Safe Mode, the computer does not process domain Group Policy Objects. Only local policies and local accounts are active. This creates a controlled environment where we can verify that local administrative access works *before* any potentially harmful GPOs are applied. It is the safest possible entry point after reconnection.

**How:**
```cmd
bcdedit /set {current} safeboot minimal
```

This sets the current boot entry to boot into Safe Mode (minimal) by default. The computer will continue booting into Safe Mode on every restart until this is removed.

**How to verify:**
```cmd
bcdedit
```
Look for `safe boot: minimal` in the current boot entry.

**What could go wrong:**
- Forgetting to remove the Safe Mode setting later, leaving the computer in a degraded state. **Mitigation**: This is addressed in Step 2 of Section 3.
- Safe Mode without networking prevents domain user login. **Mitigation**: This step is only for verifying *local* admin access. We do not need the domain user to log in during Safe Mode.

---

### Summary of pre-reconnection state

| Protection measure | Status | Recovery role |
|---|---|---|
| Built-in Administrator enabled | ✅ Must be done | Always accessible, exempt from lockout |
| Secondary local admin created | ✅ Must be done | Not affected by rename GPO |
| Domain user cached credentials | ✅ Must be verified | Allows login if DC rejects account |
| Administrators group documented | ✅ Must be done | Baseline for comparing GPO changes |
| Safe Mode boot configured | ✅ Must be done | First boot bypasses all domain GPOs |

---

## 3. Return the Computer to Domain Management

### Phase A: Reconnect and verify local access in Safe Mode

**Step A1 — Restore network connectivity**
Plug the network cable back in or re-enable Wi-Fi. The computer is configured to boot into Safe Mode, so it will not process domain GPOs on this boot.

**Step A2 — Boot and verify local admin**
1. Power on the computer. It will boot into Safe Mode.
2. Log in using the built-in Administrator account (Step 1) or the secondary local admin account (Step 2).
3. If the built-in Administrator was renamed by a previous GPO application (unlikely on this first Safe Mode boot), try the secondary local admin account instead.
4. Open an elevated Command Prompt and verify:

```cmd
whoami
net user Administrator
net localgroup Administrators
```

**If local admin does NOT work:**
- Boot from Windows installation media or a recovery USB.
- Use the Command Prompt in the recovery environment to run `net user` commands against the offline SAM. This is an advanced recovery technique and is outside the scope of this runbook.

### Phase B: Normal boot and GPO verification

**Step B1 — Remove Safe Mode boot setting**
```cmd
bcdedit /deletevalue {current} safeboot
```

**Step B2 — Boot normally**
Power cycle the computer. It will now boot normally and process domain GPOs.

**Step B3 — Verify local admin accounts survived GPO application**
1. Log in with the built-in Administrator (or its renamed version) or the secondary local admin.
2. Check what happened to the local administrator accounts:

```cmd
REM Check if the built-in Administrator was renamed
net user | findstr /i "Adm"

REM Check current Administrators group
net localgroup Administrators > C:\temp\admins_after.txt

REM Compare before and after
fc C:\temp\admins_before.txt C:\temp\admins_after.txt
```

**Step B4 — Check cached credential setting (CachedLogonsCount)**
```cmd
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v CachedLogonsCount
```
If the value is `0`, a domain GPO set it. This means cached credentials will not be usable the next time the DC is unreachable. Note this for the domain administrator.

**Step B5 — Have the domain user attempt to log in**
1. Have the user log in with their domain credentials and current domain password.
2. If the user does not know their current domain password (it may have been reset during domain restoration):
   - The user must contact the domain administrator for the new password.
   - In the meantime, the user cannot log in with their domain account.
3. Verify the user retains local admin privileges:

```cmd
whoami /groups
net localgroup Administrators
```

**If the domain user CANNOT log in or lost admin privileges:**

### Phase C: Recovery procedure

**Step C1 — Boot to Safe Mode**
```cmd
bcdedit /set {current} safeboot minimal
shutdown /r /t 0
```
Log in with the built-in Administrator or the secondary local admin account (these work in Safe Mode because domain GPOs do not apply).

**Step C2 — Fix the specific issue**

| Problem | Fix |
|---|---|
| Domain user removed from Administrators group | `net localgroup Administrators DOMAIN\username /add` |
| Built-in Administrator renamed (new name unknown) | Use the secondary local admin account: `net user RecoveryAdmin "RecoverP@ss!2024"` |
| CachedLogonsCount set to 0 | `reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v CachedLogonsCount /t REG_DWORD /d 10 /f` (note: domain GPO may override this on next refresh) |
| Domain user account locked | Wait for lockout duration, or unlock via domain controller |
| Domain user account disabled | Enable via domain controller or AD admin tools |
| Domain user password changed | Obtain new password from domain administrator |

**Step C3 — Re-enable normal boot**
```cmd
bcdedit /deletevalue {current} safeboot
shutdown /r /t 0
```

**Step C4 — Verify the fix**
- Have the domain user log in and confirm local admin privileges are present.
- Confirm the user can run elevated tasks (e.g., open an elevated Command Prompt).

### Phase D: Communicate with domain administrators

If domain GPOs are persistently removing the user from the Administrators group or disabling cached credentials, the root cause must be fixed at the domain level. Provide the domain administrator with:

1. The `gpresult /r` output showing which GPOs are applying.
2. The `net localgroup Administrators` output showing the missing user.
3. The `CachedLogonsCount` registry value if it was set to `0`.

These GPOs cannot be permanently overridden from the local machine because domain GPOs take precedence over local policy.

### Post-recovery cleanup

Once domain access is confirmed stable:
1. **Remove Safe Mode boot** (if the runbook was interrupted before Phase D).
2. **Securely destroy or rotate** the temporary recovery passwords used during this process.
3. **Re-enable the built-in Administrator account** as disabled (returning to the pre-recovery state) unless there is a specific reason to keep it enabled:
```cmd
net user Administrator /active:no
```
4. **Keep the secondary local admin account** (e.g., `RecoveryAdmin`) enabled as a standing recovery mechanism. Its password should be stored securely in a password manager or physical safe.
5. **Remove the secondary local admin** only after confirming that a proper recovery mechanism exists at the domain level (e.g., a domain-based LAPS solution for local Administrator passwords).

---

## Decision rationale: Why this approach is safest

This runbook uses **Safe Mode as the first entry point after reconnection** rather than alternatives such as disabling the Group Policy Client service (`gpsvc`):

- **Safe Mode is a built-in Windows recovery path**. It is well-tested, reliable, and does not require modifying system service configurations. Disabling `gpsvc` can break other Windows components that depend on Group Policy and is harder to reverse cleanly.
- **Safe Mode does not process domain GPOs**. This means no GPO can rename accounts, remove Administrators group membership, or change locked credential settings during the first boot. We verify that local admin access works in a clean state.
- **We establish local-independent recovery before any GPO applies**. The built-in Administrator (exempt from lockout) and a secondary local admin (not subject to rename GPOs) provide two independent recovery paths. Neither depends on domain controller availability or GPO state.
- **We avoid removing the computer from the domain** (as the objective specified). The computer remains domain-joined throughout. We only control the *order* in which domain GPOs are processed.
- **The approach is reversible and minimal**. All changes are documented and can be rolled back once domain stability is confirmed. No permanent architectural changes are made to the computer or its domain relationship.
