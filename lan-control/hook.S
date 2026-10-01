.section .text
.global local_dice_hook
local_dice_hook:
    stp x29, x30, [sp, #-128]!
    stp x20, x21, [sp, #16]
    mov x29, sp
    // Only the human local mode path can consume a command.
    adrp x9, gamemanager_slot
    ldr x9, [x9, :lo12:gamemanager_slot]
    ldr x9, [x9]
    ldr x9, [x9, #0xb8]
    ldr x9, [x9, #0x48]
    cbz x9, done
    ldrb w10, [x9, #0x8a]
    cbz w10, done
    ldrb w10, [x9, #0x89]
    cbnz w10, done
    ldrb w10, [x9, #0x8c]
    cbnz w10, done
    adrp x9, gamecontroller_slot
    ldr x9, [x9, :lo12:gamecontroller_slot]
    ldr x9, [x9]
    ldr x9, [x9, #0xb8]
    ldr x21, [x9, #0x10]
    cbz x21, done
    ldr x9, [x21, #0x800]
    cbz x9, done
    ldr w10, [x21, #0x548]
    ldr w11, [x9, #0x18]
    cmp w10, w11
    b.hs done
    add x9, x9, w10, uxtw #2
    ldr w9, [x9, #0x20]
    cbnz w9, done
    // renameat atomically claims one pending command.
    mov x0, #-100
    adr x1, pending_path
    mov x2, #-100
    adr x3, claimed_path
    mov x8, #38
    svc #0
    cbnz x0, done
    mov x0, #-100
    adr x1, claimed_path
    mov x2, #0x80000
    mov x3, #0
    mov x8, #56
    svc #0
    tbnz x0, #63, done
    mov x20, x0
    add x1, sp, #64
    mov x2, #1
    mov x8, #63
    svc #0
    str w0, [sp, #68]
    mov x0, x20
    mov x8, #57
    svc #0
    mov x0, #-100
    adr x1, claimed_path
    mov x2, #0
    mov x8, #35
    svc #0
    ldr w9, [sp, #68]
    cmp w9, #1
    b.ne done
    ldrb w20, [sp, #64]
    sub w20, w20, #48
    sub w9, w20, #1
    cmp w9, #5
    b.hi done
    // Create the genuine ObscuredInt; never write a plain int into it.
    mov w0, w20
    mov x1, #0
    add x8, sp, #32
    bl encode_int
    ldr q0, [sp, #32]
    ldr w9, [sp, #48]
    stur q0, [x19, #0x20]
    stur w9, [x19, #0x30]
    ldr x9, [x19, #0xa8]
    cbz x9, record
    sub w10, w20, #1
    add x9, x9, w10, uxtw #3
    ldr x9, [x9, #0x20]
    str x9, [x19, #0xb0]
    cmp w20, #6
    b.ne record
    // A commanded six closes this player's opening phase and drought.
    ldr w10, [x21, #0x548]
    sub w11, w10, #1
    cmp w11, #5
    b.hi record
    adr x9, seen_offsets
    ldrb w11, [x9, w11, uxtw]
    mov w12, #1
    strb w12, [x19, x11]
    ldr x9, [x19, #0x98]
    cbz x9, record
    add x9, x9, w10, uxtw #2
    str wzr, [x9, #0x20]
record:
    mov x0, #-100
    adr x1, last_path
    mov x2, #577
    mov x3, #384
    mov x8, #56
    svc #0
    tbnz x0, #63, done
    mov x20, x0
    add x1, sp, #64
    mov x2, #1
    mov x8, #64
    svc #0
    mov x0, x20
    mov x8, #57
    svc #0
done:
    ldp x20, x21, [sp, #16]
    mov x0, x19
    ldp x29, x30, [sp], #128
    ret
seen_offsets:
    .byte 0x65, 0x62, 0x64, 0x63, 0x61, 0x60
pending_path:
    .asciz "/data/user/0/com.ludo.king.lan/files/nextdice"
claimed_path:
    .asciz "/data/user/0/com.ludo.king.lan/files/nextdice.claimed"
last_path:
    .asciz "/data/user/0/com.ludo.king.lan/files/lastdice"
.balign 4
.global hide_gems_ads
hide_gems_ads:
 stp x19, x30, [sp, #-16]!
 mov x19, x0
 ldr x0, [x19, #0x20]
 cbz x0, 1f
 mov x1, xzr
 bl get_game_object
 cbz x0, 1f
 mov w1, wzr
 mov x2, xzr
 bl set_active
1:
 ldr x0, [x19, #0x28]
 cbz x0, 2f
 mov w1, wzr
 mov x2, xzr
 bl set_active
2:
 ldp x19, x30, [sp], #16
 ret
.global dismiss_local_ad_offer
dismiss_local_ad_offer:
 mov x0, x19
 mov x1, xzr
 ldp x20, x19, [sp, #0x20]
 ldp x22, x21, [sp, #0x10]
 ldr x30, [sp], #0x30
 b dismiss_local_offer
.global hide_coins_ads
hide_coins_ads:
 stp x19, x30, [sp, #-16]!
 mov x19, x0
 ldr x0, [x19, #0x30]
 cbz x0, 3f
 mov w1, wzr
 mov x2, xzr
 bl set_active
3:
 ldr x0, [x19, #0x38]
 cbz x0, 4f
 mov w1, wzr
 mov x2, xzr
 bl set_active
4:
 ldr x0, [x19, #0x40]
 cbz x0, 5f
 mov w1, wzr
 mov x2, xzr
 bl set_active
5:
 ldp x19, x30, [sp], #16
 ret
