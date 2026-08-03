# Security and Approval State Architecture - Mko-AINotify Part 3  
## 1. Internal Module Architecture  
  
### SecurityModule  
  
Purpose: Cryptographic operations and secret management for callback integrity. 
Bootstrap Flow: 1. First run generate 32-byte random secret 2. Store in SecretStorage 3. On restart retrieve or generate new  
  
### ApprovalStateManager  
  
Purpose: In-memory state tracking for pending approvals.  
  
State: pendingMap, handleMap, dedupeSet, TTL sweeper. 
## Layer Interaction Diagram  
  
Connector registerPending -> ApprovalStateManager signCallback -> SecurityModule -> returns signed tokens to TelegramProvider -> sendMessage -> user taps -> callback_query via getUpdates -> handleCallbackQuery -> validateAndConsume -> editMessage -> replyToPermission 
## 42-Byte Envelope Layout  
Formula ceil 42 times 4 over 3 equals 56 chars less than 64 limit  
Fields version 1 action 1 handle 8 nonce 8 expiry 8 hmac 16 equals 42 bytes  
  
## Persistence Design  
SecretStorage encrypts secrets at OS level  
globalState survives reloads but limited to 5MB  
  
## Risks and Mitigations  
Replay window mitigated by nonce and expiry  
Secret loss generate new and document  
Handle collision negligible at 264  
Race condition handled by callback_query_id dedupe  
  
## Sources  
VS Code SecretStorage API Electron SafeStorage  
Telegram callback_data limit 64 bytes  
NIST SP 800-107 Truncated HMAC guidelines 
## Detailed Module Structure 
