package com.snesflow.android

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import android.view.HapticFeedbackConstants
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import kotlin.math.abs
import kotlin.math.hypot

class TouchControlsView(
    context: Context,
    private val onKey: (keyCode: Int, pressed: Boolean) -> Unit,
    private val onSave: () -> Unit,
    private val onLoad: () -> Unit,
) : View(context) {

    private data class CircleButton(val cx: Float, val cy: Float, val r: Float, val key: Int, val label: String)
    private data class RectButton(val rect: RectF, val key: Int?, val label: String, val action: (() -> Unit)? = null)

    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(118, 18, 18, 18) }
    private val pressedFill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(185, 70, 70, 70) }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(225, 255, 255, 255)
        style = Paint.Style.STROKE
        strokeWidth = dp(1.7f)
    }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textAlign = Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }
    private val stickBase = Paint(Paint.ANTI_ALIAS_FLAG)
    private val stickKnob = Paint(Paint.ANTI_ALIAS_FLAG)

    private var actionButtons: List<CircleButton> = emptyList()
    private var rects: List<RectButton> = emptyList()

    private var stickCx = 0f
    private var stickCy = 0f
    private var stickRadius = 0f
    private var stickKnobRadius = 0f
    private var stickKnobX = 0f
    private var stickKnobY = 0f
    private var stickPointerId: Int? = null
    private val stickKeys = mutableSetOf<Int>()

    private val pointerKeys = mutableMapOf<Int, Int>()
    private val pointerActions = mutableMapOf<Int, Pair<RectF, () -> Unit>>()
    private val pressedKeys = mutableSetOf<Int>()

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        rebuildRegions(w.toFloat(), h.toFloat())
    }

    private fun rebuildRegions(w: Float, h: Float) {
        val unit = (h * 0.105f).coerceIn(dp(42f), dp(78f))

        stickCx = w * 0.105f
        stickCy = h * 0.73f
        stickRadius = (h * 0.135f).coerceIn(dp(76f), dp(120f))
        stickKnobRadius = stickRadius * 0.52f
        stickKnobX = stickCx
        stickKnobY = stickCy

        val rightX = w * 0.895f
        val baseY = h * 0.73f
        val gap = unit * 0.95f

        // X é desenhado separadamente pela GameActivity como botão de dupla função.
        // Y foi removido da interface. A e B permanecem diretos no RetroPad.
        actionButtons = listOf(
            CircleButton(rightX + gap, baseY, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_A, "A"),
            CircleButton(rightX, baseY + gap, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_B, "B"),
        )

        val centerY = h * 0.915f
        val smallW = w * 0.085f
        val smallH = h * 0.075f
        fun centeredRect(cx: Float) = RectF(cx - smallW / 2, centerY - smallH / 2, cx + smallW / 2, centerY + smallH / 2)

        rects = listOf(
            RectButton(centeredRect(w * 0.35f), KeyEvent.KEYCODE_BUTTON_SELECT, "SELECT"),
            RectButton(centeredRect(w * 0.45f), null, "SAVE", onSave),
            RectButton(centeredRect(w * 0.55f), null, "LOAD", onLoad),
            RectButton(centeredRect(w * 0.65f), KeyEvent.KEYCODE_BUTTON_START, "START"),
        )

        stickBase.shader = RadialGradient(
            stickCx, stickCy, stickRadius,
            intArrayOf(Color.rgb(62, 62, 66), Color.rgb(15, 15, 17)),
            floatArrayOf(0f, 1f),
            Shader.TileMode.CLAMP,
        )
        stickKnob.shader = RadialGradient(
            stickCx - stickKnobRadius * 0.2f,
            stickCy - stickKnobRadius * 0.25f,
            stickKnobRadius * 1.35f,
            intArrayOf(Color.rgb(92, 92, 98), Color.rgb(20, 20, 22)),
            floatArrayOf(0f, 1f),
            Shader.TileMode.CLAMP,
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        canvas.drawCircle(stickCx, stickCy, stickRadius, stickBase)
        canvas.drawCircle(stickCx, stickCy, stickRadius, border)
        canvas.drawCircle(stickKnobX, stickKnobY, stickKnobRadius, stickKnob)
        canvas.drawCircle(stickKnobX, stickKnobY, stickKnobRadius, border)

        actionButtons.forEach { b ->
            canvas.drawCircle(b.cx, b.cy, b.r, if (b.key in pressedKeys) pressedFill else fill)
            canvas.drawCircle(b.cx, b.cy, b.r, border)
            text.textSize = b.r * 0.70f
            val baseline = b.cy - (text.ascent() + text.descent()) / 2
            canvas.drawText(b.label, b.cx, baseline, text)
        }

        rects.forEach { b ->
            val isPressed = b.key != null && b.key in pressedKeys
            canvas.drawRoundRect(b.rect, dp(16f), dp(16f), if (isPressed) pressedFill else fill)
            canvas.drawRoundRect(b.rect, dp(16f), dp(16f), border)
            text.textSize = (b.rect.height() * 0.34f).coerceAtLeast(dp(12f))
            val baseline = b.rect.centerY() - (text.ascent() + text.descent()) / 2
            canvas.drawText(b.label, b.rect.centerX(), baseline, text)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val i = event.actionIndex
                pressPointer(event.getPointerId(i), event.getX(i), event.getY(i))
            }

            MotionEvent.ACTION_MOVE -> {
                for (i in 0 until event.pointerCount) {
                    val id = event.getPointerId(i)
                    val x = event.getX(i)
                    val y = event.getY(i)

                    if (stickPointerId == id) {
                        updateStick(x, y)
                        continue
                    }

                    if (pointerKeys.containsKey(id)) continue

                    pointerActions[id]?.let { (rect, _) ->
                        if (!rect.contains(x, y)) pointerActions.remove(id)
                    }
                }
            }

            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP -> releasePointer(event.getPointerId(event.actionIndex))
            MotionEvent.ACTION_CANCEL -> releaseAll()
        }
        return true
    }

    private fun pressPointer(id: Int, x: Float, y: Float) {
        if (stickPointerId == null && hypot(x - stickCx, y - stickCy) <= stickRadius * 1.35f) {
            stickPointerId = id
            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
            updateStick(x, y)
            return
        }

        keyAt(x, y)?.let { key ->
            pointerKeys[id] = key
            pressKey(key)
            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
            return
        }

        rects.firstOrNull { it.action != null && it.rect.contains(x, y) }?.let { button ->
            pointerActions[id] = button.rect to requireNotNull(button.action)
            performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
        }
    }

    private fun updateStick(x: Float, y: Float) {
        val dx = x - stickCx
        val dy = y - stickCy
        val distance = hypot(dx, dy)
        val maxTravel = stickRadius - stickKnobRadius * 0.72f
        val scale = if (distance > maxTravel && distance > 0f) maxTravel / distance else 1f
        stickKnobX = stickCx + dx * scale
        stickKnobY = stickCy + dy * scale

        val deadZone = stickRadius * 0.23f
        val next = mutableSetOf<Int>()
        if (distance >= deadZone) {
            val nx = dx / stickRadius
            val ny = dy / stickRadius
            if (nx <= -0.30f) next += KeyEvent.KEYCODE_DPAD_LEFT
            if (nx >= 0.30f) next += KeyEvent.KEYCODE_DPAD_RIGHT
            if (ny <= -0.30f) next += KeyEvent.KEYCODE_DPAD_UP
            if (ny >= 0.30f) next += KeyEvent.KEYCODE_DPAD_DOWN

            if (next.isEmpty()) {
                if (abs(nx) > abs(ny)) next += if (nx < 0) KeyEvent.KEYCODE_DPAD_LEFT else KeyEvent.KEYCODE_DPAD_RIGHT
                else next += if (ny < 0) KeyEvent.KEYCODE_DPAD_UP else KeyEvent.KEYCODE_DPAD_DOWN
            }
        }

        (stickKeys - next).forEach { releaseKey(it) }
        (next - stickKeys).forEach { pressKey(it) }
        stickKeys.clear()
        stickKeys.addAll(next)
        invalidate()
    }

    private fun releasePointer(id: Int) {
        if (stickPointerId == id) {
            stickKeys.toList().forEach { releaseKey(it) }
            stickKeys.clear()
            stickPointerId = null
            stickKnobX = stickCx
            stickKnobY = stickCy
            invalidate()
            return
        }

        pointerKeys.remove(id)?.let { releaseKey(it) }
        pointerActions.remove(id)?.second?.invoke()
    }

    private fun pressKey(key: Int) {
        if (pressedKeys.add(key)) onKey(key, true)
        invalidate()
    }

    private fun releaseKey(key: Int) {
        if (pressedKeys.remove(key)) onKey(key, false)
        invalidate()
    }

    private fun releaseAll() {
        (pressedKeys + stickKeys).toSet().forEach { onKey(it, false) }
        pressedKeys.clear()
        stickKeys.clear()
        pointerKeys.clear()
        pointerActions.clear()
        stickPointerId = null
        stickKnobX = stickCx
        stickKnobY = stickCy
        invalidate()
    }

    private fun keyAt(x: Float, y: Float): Int? {
        actionButtons.firstOrNull { button ->
            hypot(x - button.cx, y - button.cy) <= button.r * 1.22f
        }?.let { return it.key }

        rects.firstOrNull { it.key != null && it.rect.contains(x, y) }?.let { return it.key }
        return null
    }

    private fun dp(v: Float): Float = v * resources.displayMetrics.density
}
