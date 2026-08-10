# Windows Domain Recovery Runbook: Preventing User Lockout

## 1. Context

### Authentication Risks After Domain Restoration

When a restored Active Directory becomes available, a domain-joined computer will reconnect and begin receiving Group Policy Objects (GPOs) from domain controllers. These restored policies can disrupt access in several ways:

| Risk | Mechanism | Impact |
|---|---|---|
| Password reset | Domain password changed or reset during restoration | Cached credentials match the *old* password only |
| Account lockout | Wrong password entered against a live DC; or domain lockout policy applied | Account cannot authenticate even with cached credentials if a DC responds |
| Account disabled | Domain user disabled in AD | Login rejected outright; cached credentials not consulted when a DC is reachable |
| Local Admins group removal | Restricted Groups or Local Users and Groups GPO preference | User can log in but cannot elevate to administrator |
| Local account disable | "Accounts: Administrator account status" GPO set to Disabled | Built-in Administrator cannot be used for recovery after GPO applies |
| Cached credential count set to 0 | "Interactive logon: Number of previous logons to cache" GPO set to 0 | No cached logons possible when DC is unreachable |

### Domain-Dependent vs. Local-Independent Access

**Domain-dependent access** relies on a domain controller for authentication:
- Account lockout, disablement, and password changes are enforced by the DC.
- Cached credentials (last 10 logons by default) allow offline login, but only if a DC is unreachable and the cache count has not been set to zero by GPO.
- Group membership is dynamic — a GPO can strip admin rights on the next startup or refresh.

**Local-independent access** relies on accounts stored in the local SAM:
- The **built-in Administrator account** (RID 500) is always a local account, always retains admin rights, and is **exempt from account lockout policies**.
- **Locally created user accounts** in the Administrators group survive domain failures as long as no GPO overwrites local group membership.
- Local accounts work regardless of domain controller availability.

### Key Technical Facts

- **Built-in Administrator (RID 500)** cannot be locked out, only renamed or disabled by GPO. In Safe Mode, domain GPOs are not processed, so the account retains its status (enabled or disabled) from the last local configuration.
- **Cached credentials** are a hash of the password last used to log in interactively. If the domain password changes, the cache will not match, and login will fail even for cached sign-in.
- **Safe Mode** boots Windows with a minimal set of drivers and services. Domain Group Policy is **not** applied during Safe Mode, and the Group Policy Client service (`gpsvc`) does not refresh policies. This makes Safe Mode a controlled environment for verifying local access before any domain policies are applied.

### Strategy Overview

Before reconnecting to the restored domain:
1. Establish two independent local administrator recovery paths (built-in Administrator + secondary local admin).
2. Verify that the domain user has cached credentials.
3. Document the current Administrators group membership.
4. Configure the computer to boot into Safe Mode so local access can be verified before GPOs are processed.

The Safe Mode technique is used because it is a built-in Windows mechanism that does not require modifying system services or removing the computer from the domain. It is reversible and minimal.

---

## 2. Protect the Computer Before Domain Policies Are Restored

> **Prerequisite**: Log in now using the domain user account with cached credentials (domain is currently unreachable). This user has local administrator privileges and can run elevated commands. If the domain user cannot log in, boot to Safe Mode and use the built-in Administrator account (if already enabled) or a Windows PE recovery environment.

### Step 1: Enable and Secure the Built-in Administrator Account

| Element | Detail |
|---|---|
| **What to do** | Enable the built-in local Administrator account (RID 500) and set a strong, unique password. |
| **Why** | The built-in Administrator is always a local account, always retains admin rights, and is exempt from account lockout policies. It is the most reliable recovery path after GPO application. Even if a GPO disables it, Safe Mode retains the last-known enabled state. |
| **How to do it** | Open an elevated Command Prompt (as Administrator) and run: |

```cmd
net user Administrator "Str0ngP@ssw0rd!2024" /active:yes /expires:never
```

| **How to verify** | Run: |

```cmd
net user Administrator
```

Confirm the output shows `Account active: Yes`.

| **What could go wrong** | If the "Accounts: Rename administrator account" GPO later renames this account, the name "Administrator" will no longer exist — but the account still exists under its new name with the same password. The secondary account (Step 2) covers this scenario. If the password is weak or reused, it is a security risk — use a long, random password unique to this machine. |

### Step 2: Create a Secondary Local Administrator Account

| Element | Detail |
|---|---|
| **What to do** | Create a new local user account, add it to the local Administrators group, and set a strong password. |
| **Why** | The "Accounts: Rename administrator account" GPO only affects the built-in Administrator (RID 500). A separately created admin account with a different name will not be renamed by this policy. This provides a second recovery path that is not subject to the rename GPO. |
| **How to do it** | In the same elevated Command Prompt: |

```cmd
net user RecoveryAdmin "RecoverP@ss!2024" /add /expires:never
net localgroup Administrators RecoveryAdmin /add
```

| **How to verify** | Run: |

```cmd
net user RecoveryAdmin
net localgroup Administrators
```

Confirm `RecoveryAdmin` appears in the Administrators group listing.

| **What could go wrong** | A Restricted Groups GPO could remove `RecoveryAdmin` from the Administrators group at the next normal boot. However, this account survives in Safe Mode (where GPOs are not processed) and can be used to diagnose and fix the issue. Use a strong password; treat it as a recovery credential. |

### Step 3: Verify Domain User Cached Credentials

| Element | Detail |
|---|---|
| **What to do** | Ensure the domain user can log in without a live domain controller by logging in while the network is disconnected. |
| **Why** | When the domain is restored and GPOs are applied, the domain user's account might be locked, disabled, or have its password changed. If cached credentials exist, the user can still log in using their last-known password when the DC cannot be reached. |
| **How to do it** | 1. Disconnect the network (unplug Ethernet or disable Wi-Fi).<br>2. Have the domain user log in with their domain credentials as usual.<br>3. If login succeeds, cached credentials are now stored.<br>4. Verify the cache count: |

```cmd
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v CachedLogonsCount
```

The default value is `10`. Any value greater than `0` allows cached credential use.

| **How to verify** | The user successfully logged in while offline. `CachedLogonsCount` is greater than `0`. |
| **What could go wrong** | If the user does not remember their last password, cached credentials will not help. The local admin accounts (Steps 1 and 2) provide the independent recovery path. If a GPO sets `CachedLogonsCount` to `0` after reconnection, cached credentials will stop working — check this value again after the first normal boot (Section 3, Step B4). |

### Step 4: Document Current Local Administrators Group Membership

| Element | Detail |
|---|---|
| **What to do** | Record the current members of the local Administrators group for before/after comparison. |
| **Why** | After domain GPOs apply, Restricted Groups policies may alter the membership of the local Administrators group. Having a baseline allows quick identification of what changed and what needs to be restored. |
| **How to do it** | In the elevated Command Prompt: |

```cmd
net localgroup Administrators > C:\temp\admins_before.txt
```

Save this file to external media (USB drive) in case the computer becomes inaccessible.

| **How to verify** | Review the file contents to ensure the domain user appears in the list. |
| **What could go wrong** | Forgetting to save the baseline before reconnection is the primary risk. Store the file externally. |

### Step 5: Configure Safe Mode Boot for First Reconnection

| Element | Detail |
|---|---|
| **What to do** | Set the computer to boot into Safe Mode on the next startup using `bcdedit`. |
| **Why** | In Safe Mode, the computer does not process domain Group Policy Objects. Only local policies and local accounts are active. This creates a controlled environment where we can verify that local administrative access works *before* any potentially harmful GPOs are applied. It is the safest possible entry point after reconnection. |
| **How to do it** | In the elevated Command Prompt: |

```cmd
bcdedit /set {current} safeboot minimal
```

This sets the current boot entry to boot into Safe Mode (minimal) by default. The computer will continue booting into Safe Mode on every restart until this is removed.

| **How to verify** | Run: |

```cmd
bcdedit
```

Look for `safe boot: minimal` in the current boot entry.

| **What could go wrong** | Forgetting to remove the Safe Mode setting later leaves the computer in a degraded state. This is addressed in Step B1 of Section 3. Safe Mode without networking prevents domain user login — but this step is only for verifying *local* admin access, not domain access. |

### Pre-Reconnection Protection Summary

| Protection measure | Recovery role |
|---|---|
| Built-in Administrator enabled (Step 1) | Always accessible, exempt from lockout |
| Secondary local admin created (Step 2) | Not affected by rename GPO, works in Safe Mode |
| Domain user cached credentials (Step 3) | Allows login if DC rejects account |
| Administrators group documented (Step 4) | Baseline for comparing GPO changes |
| Safe Mode boot configured (Step 5) | First boot bypasses all domain GPOs |

---

## 3. Return the Computer to Domain Management

### Phase A: Reconnect and Verify Local Access in Safe Mode

**Step A1 — Restore network connectivity**

Plug the network cable back in or re-enable Wi-Fi. The computer is configured to boot into Safe Mode, so it will not process domain GPOs on this boot.

**Step A2 — Boot and verify local admin**

1. Power on the computer. It will boot into Safe Mode.
2. Log in using the built-in Administrator account (Step 1) or the secondary local admin account (Step 2).
3. If the built-in Administrator was renamed by a *previous* GPO application cycle (unlikely on this first Safe Mode boot since GPO is not processed in Safe Mode), use the secondary local admin account instead.
4. Open an elevated Command Prompt and verify:

```cmd
whoami
net user Administrator
net localgroup Administrators
```

**If local admin does NOT work in Safe Mode:**

- Boot from Windows installation media or a recovery USB.
- Use the Command Prompt in the recovery environment to run `net user` commands against the offline SAM. This is an advanced recovery technique outside the scope of this runbook.

### Phase B: Normal Boot and GPO Verification

**Step B1 — Remove Safe Mode boot setting**

```cmd
bcdedit /deletevalue {current} safeboot
```

**Step B2 — Boot normally**

Power cycle the computer. It will now boot normally and process domain GPOs.

**Step B3 — Verify local admin accounts survived GPO application**

1. Log in with the built-in Administrator (or its renamed version) or the secondary local admin account.
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

If the value is `0`, a domain GPO set it. This means cached credentials will not be usable the next time the DC is unreachable. Note this for the domain administrator (Phase D).

**Step B5 — Have the domain user attempt to log in**

1. Have the user log in with their domain credentials and current domain password.
2. If the user does not know their current domain password (it may have been reset during domain restoration):
   - The user must contact the domain administrator for the new password.
   - In the meantime, local admin accounts provide independent access.
3. Verify the user retains local admin privileges:

```cmd
whoami /groups
net localgroup Administrators
```

### Phase C: Recovery Procedure If Access Is Lost

If the restored GPOs cause any access issue, follow this escalation path:

**Step C1 — Boot to Safe Mode**

```cmd
bcdedit /set {current} safeboot minimal
shutdown /r /t 0
```

Log in with the built-in Administrator or the secondary local admin account. These work in Safe Mode because domain GPOs do not apply.

**Step C2 — Fix the specific issue**

| Problem | Fix |
|---|---|
| Domain user removed from Administrators group | `net localgroup Administrators DOMAIN\username /add` |
| Built-in Administrator renamed (new name unknown) | Use the secondary local admin account: `net user RecoveryAdmin "RecoverP@ss!2024"` |
| CachedLogonsCount set to 0 | `reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v CachedLogonsCount /t REG_DWORD /d 10 /f` (note: domain GPO may override this on next refresh) |
| Domain user account locked | Wait for lockout duration, or unlock via domain controller |
| Domain user account disabled | Enable via domain controller or AD admin tools |
| Domain user password changed | Obtain new password from domain administrator |
| Built-in Administrator disabled by GPO | `net user Administrator /active:yes` (works in Safe Mode where GPO is not applied) |

**Step C3 — Re-enable normal boot**

```cmd
bcdedit /deletevalue {current} safeboot
shutdown /r /t 0
```

**Step C4 — Verify the fix**

- Have the domain user log in and confirm local admin privileges are present.
- Confirm the user can run elevated tasks (e.g., open an elevated Command Prompt).

### Phase D: Communicate with Domain Administrators

If domain GPOs are persistently removing the user from the Administrators group, disabling cached credentials, or disabling local accounts, the root cause must be fixed at the domain level. GPOs take precedence over local policy and cannot be permanently overridden from the local machine.

Provide the domain administrator with:

1. **Which GPOs are applying**: `gpresult /r` output (saved to file while in normal boot).
2. **What changed**: `net localgroup Administrators` output showing the missing user.
3. **Cached credential setting**: `CachedLogonsCount` value if it was set to `0`.
4. **Local account status**: Whether the built-in Administrator was disabled or renamed.

### Phase E: Post-Recovery Cleanup

Once domain access is confirmed stable:

1. **Remove Safe Mode boot** (if interrupted before Phase D):
   ```cmd
   bcdedit /deletevalue {current} safeboot
   ```

2. **Securely store or rotate** the temporary recovery passwords. Do not leave known passwords in documentation. Consider using a password manager or physical safe.

3. **Decide on the built-in Administrator account**:
   - If domain GPO manages local Administrator passwords (e.g., LAPS), ensure LAPS is functional before disabling.
   - If no LAPS exists, keep the built-in Administrator enabled with a strong password as a standing recovery mechanism.
   - To disable (if desired): `net user Administrator /active:no`

4. **Keep the secondary local admin account** (e.g., `RecoveryAdmin`) as a permanent recovery mechanism. Store its password securely.

---

### Test on One Computer First

Before applying this procedure to all computers:

1. Select one non-critical machine and follow all steps from Section 2.
2. Complete Phases A through D of Section 3 on this machine.
3. Confirm the domain user can log in and retains local admin privileges.
4. Only after successful verification, repeat the procedure on remaining computers.
