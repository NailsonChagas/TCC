	.cpu cortex-m7
	.arch armv7e-m
	.fpu fpv5-sp-d16
	.eabi_attribute 27, 1
	.eabi_attribute 28, 1
	.eabi_attribute 20, 1
	.eabi_attribute 21, 1
	.eabi_attribute 23, 3
	.eabi_attribute 24, 1
	.eabi_attribute 25, 1
	.eabi_attribute 26, 1
	.eabi_attribute 30, 2
	.eabi_attribute 34, 1
	.eabi_attribute 18, 4
	.file	"buck_model.c"
	.text
	.align	1
	.p2align 2,,3
	.global	buck_step
	.syntax unified
	.thumb
	.thumb_func
	.type	buck_step, %function
buck_step:
	@ args = 0, pretend = 0, frame = 8
	@ frame_needed = 0, uses_anonymous_args = 0
	@ link register save eliminated.
	sub	sp, sp, #8
	ldr	r2, [r0]	@ float
	ldr	r3, [r0, #4]	@ float
	str	r2, [sp]	@ float
	str	r3, [sp, #4]	@ float
	cbz	r1, .L2
	vldr.32	s8, [sp]
	vldr.32	s12, .L6
	vldr.32	s15, [sp, #4]
	vldr.32	s13, .L6+4
	vldr.32	s10, [sp]
	vmul.f32	s15, s15, s12
	vldr.32	s14, [sp, #4]
	vldr.32	s9, .L6+8
	vmul.f32	s14, s14, s13
	vldr.32	s11, .L6+12
	vfma.f32	s15, s8, s9
	vldr.32	s12, .L6+16
	vldr.32	s13, .L6+20
	vfma.f32	s14, s10, s11
	vadd.f32	s15, s15, s12
	vadd.f32	s14, s14, s13
	vstr.32	s15, [r0]
	vstr.32	s14, [r0, #4]
	add	sp, sp, #8
	@ sp needed
	bx	lr
.L2:
	vldr.32	s9, [sp]
	vldr.32	s12, .L6
	vldr.32	s15, [sp, #4]
	vldr.32	s13, .L6+4
	vldr.32	s11, [sp]
	vmul.f32	s15, s15, s12
	vldr.32	s14, [sp, #4]
	vldr.32	s10, .L6+8
	vmul.f32	s14, s14, s13
	vldr.32	s12, .L6+12
	vfma.f32	s15, s9, s10
	vldr.32	s13, .L6+24
	vfma.f32	s14, s11, s12
	vadd.f32	s15, s15, s13
	vadd.f32	s14, s14, s13
	vstr.32	s15, [r0]
	vstr.32	s14, [r0, #4]
	add	sp, sp, #8
	@ sp needed
	bx	lr
.L7:
	.align	2
.L6:
	.word	-1190529564
	.word	1064910863
	.word	1065351984
	.word	1066161976
	.word	1004171951
	.word	997233879
	.word	0
	.size	buck_step, .-buck_step
	.global	__aeabi_f2d
	.section	.rodata.str1.4,"aMS",%progbits,1
	.align	2
.LC0:
	.ascii	"iL = %.6f\012\000"
	.align	2
.LC1:
	.ascii	"vC = %.6f\012\000"
	.section	.text.startup,"ax",%progbits
	.align	1
	.p2align 2,,3
	.global	main
	.syntax unified
	.thumb
	.thumb_func
	.type	main, %function
main:
	@ args = 0, pretend = 0, frame = 8
	@ frame_needed = 0, uses_anonymous_args = 0
	push	{r4, r5, r6, r7, lr}
	movs	r3, #0
	sub	sp, sp, #12
	movs	r4, #0
	ldr	r7, .L12
	movs	r6, #100
	movw	r5, #29998
	str	r3, [sp]	@ float
	str	r3, [sp, #4]	@ float
.L9:
	umull	r3, r1, r7, r4
	mov	r0, sp
	lsrs	r1, r1, #5
	mls	r1, r6, r1, r4
	adds	r4, r4, #1
	cmp	r1, #49
	ite	hi
	movhi	r1, #0
	movls	r1, #1
	bl	buck_step
	cmp	r4, r5
	bne	.L9
	ldr	r0, [sp]	@ float
	bl	__aeabi_f2d
	mov	r2, r0
	mov	r3, r1
	ldr	r0, .L12+4
	bl	printf
	ldr	r0, [sp, #4]	@ float
	bl	__aeabi_f2d
	mov	r2, r0
	mov	r3, r1
	ldr	r0, .L12+8
	bl	printf
	movs	r0, #0
	add	sp, sp, #12
	@ sp needed
	pop	{r4, r5, r6, r7, pc}
.L13:
	.align	2
.L12:
	.word	1374389535
	.word	.LC0
	.word	.LC1
	.size	main, .-main
	.ident	"GCC: (15:13.2.rel1-2) 13.2.1 20231009"
