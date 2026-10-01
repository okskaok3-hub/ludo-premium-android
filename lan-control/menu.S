.text
.global _start
_start:
 stp x19, x30, [sp, #-16]!
 mov x19, x0
 strb wzr, [x0, #0x118]
 ldr x0, [x0, #0x110]
 cbz x0, load
 mov x1, xzr
 bl get_game_object
 cbz x0, load
 mov w1, wzr
 mov x2, xzr
 bl set_active
load:
 mov x0, x19
 mov x1, xzr
 bl init_ads
 mov x0, x19
 mov x1, xzr
 ldp x19, x30, [sp], #16
 b load_main_menu
