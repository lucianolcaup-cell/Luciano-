package com.snesflow.android

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot

class TouchControlsView(
    context: Context,
    private val onKey: (keyCode: Int, pressed: Boolean) -> Unit,
    private val onSave: () -> Unit,
    private val onLoad: () -> Unit,
) : View(context) {
    private data class CircleButton(val cx: Float, val cy: Float, val r: Float, val key: Int, val label: String)
    private data class RectButton(val rect: RectF, val key: Int?, val label: String, val action: (() -> Unit)? = null)

    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(125, 18, 18, 18) }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(210, 255, 255, 255)
        style = Paint.Style.STROKE
        strokeWidth = dp(1.5f)
    }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textAlign = Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }

    private val activeKeys = mutableMapOf<Int, Int>()
    private val pointerActions = mutableMapOf<Int, () -> Unit>()
    private var circles: List<CircleButton> = emptyList()
    private var rects: List<RectButton> = emptyList()

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        rebuildRegions(w.toFloat(), h.toFloat())
    }

    private fun rebuildRegions(w: Float, h: Float) {
        val unit = (h * 0.105f).coerceIn(dp(42f), dp(78f))
        val leftX = w * 0.105f
        val baseY = h * 0.73f
        val rightX = w * 0.895f
        val gap = unit * 0.95f
        circles = listOf(
            CircleButton(leftX, baseY - gap, unit * 0.48f, KeyEvent.KEYCODE_DPAD_UP, "▲"),
            CircleButton(leftX - gap, baseY, unit * 0.48f, KeyEvent.KEYCODE_DPAD_LEFT, "◀"),
            CircleButton(leftX + gap, baseY, unit * 0.48f, KeyEvent.KEYCODE_DPAD_RIGHT, "▶"),
            CircleButton(leftX, baseY + gap, unit * 0.48f, KeyEvent.KEYCODE_DPAD_DOWN, "▼"),
            CircleButton(rightX, baseY - gap, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_X, "X"),
            CircleButton(rightX - gap, baseY, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_Y, "Y"),
            CircleButton(rightX + gap, baseY, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_A, "A"),
            CircleButton(rightX, baseY + gap, unit * 0.48f, KeyEvent.KEYCODE_BUTTON_B, "B"),
        )

        val shoulderW = w * 0.115f
        val shoulderH = h * 0.09f
        val side = w * 0.035f
        val top = h * 0.035f
        val centerY = h * 0.915f
        val smallW = w * 0.105f
        val smallH = h * 0.075f
        rects = listOf(
            RectButton(RectF(side, top, side + shoulderW, top + shoulderH), KeyEvent.KEYCODE_BUTTON_L1, "L"),
            RectButton(RectF(w - side - shoulderW, top, w - side, top + shoulderH), KeyEvent.KEYCODE_BUTTON_R1, "R"),
            RectButton(RectF(w * 0.38f - smallW, centerY - smallH / 2, w * 0.38f, centerY + smallH / 2), KeyEvent.KEYCODE_BUTTON_SELECT, "SELECT"),
            RectButton(RectF(w * 0.62f, centerY - smallH / 2, w * 0.62f + smallW, centerY + smallH / 2), KeyEvent.KEYCODE_BUTTON_START, "START"),
            RectButton(RectF(w * 0.445f - smallW, centerY - smallH / 2, w * 0.445f, centerY + smallH / 2), null, "SAVE", onSave),
            RectButton(RectF(w * 0.555f, centerY - smallH / 2, w * 0.555f + smallW, centerY + smallH / 2), null, "LOAD", onLoad),
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        circles.forEach { b ->
            canvas.drawCircle(b.cx, b.cy, b.r, fill)
            canvas.drawCircle(b.cx, b.cy, b.r, border)
            text.textSize = b.r * 0.70f
            val baseline = b.cy - (text.ascent() + text.descent()) / 2
            canvas.drawText(b.label, b.cx, baseline, text)
        }
        rects.forEach { b ->
            canvas.drawRoundRect(b.rect, dp(16f), dp(16f), fill)
            canvas.drawRoundRect(b.rect, dp(16f), dp(16f), border)
            text.textSize = (b.rect.height() * 0.34f).coerceAtLeast(dp(12f))
            val baseline = b.rect.centerY() - (text.ascent() + text.descent()) / 2
            canvas.drawText(b.label, b.rect.centerX(), baseline, text)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val index = event.actionIndex
                pressPointer(event.getPointerId(index), event.getX(index), event.getY(index))
            }
            MotionEvent.ACTION_MOVE -> {
                for (i in 0 until event.pointerCount) {
                    val id = event.getPointerId(i)
                    val current = activeKeys[id]
                    val target = keyAt(event.getX(i), event.getY(i))
                    if (current != target) {
                        if (current != null) onKey(current, false)
                        if (target != null) onKey(target, true)
                        if (target == null) activeKeys.remove(id) else activeKeys[id] = target
                    }
                }
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP -> releasePointer(event.getPointerId(event.actionIndex))
            MotionEvent.ACTION_CANCEL -> releaseAll()
        }
        return true
    }

    private fun pressPointer(id: Int, x: Float, y: Float) {
        keyAt(x, y)?.let { key ->
            activeKeys[id] = key
            onKey(key, true)
            return
        }
        actionAt(x, y)?.let { pointerActions[id] = it }
    }

    private fun releasePointer(id: Int) {
        activeKeys.remove(id)?.let { onKey(it, false) }
        pointerActions.remove(id)?.invoke()
    }

    private fun releaseAll() {
        activeKeys.values.distinct().forEach { onKey(it, false) }
        activeKeys.clear()
        pointerActions.clear()
    }

    private fun keyAt(x: Float, y: Float): Int? {
        circles.firstOrNull { hypot(x - it.cx, y - it.cy) <= it.r * 1.15f }?.let { return it.key }
        rects.firstOrNull { it.key != null && it.rect.contains(x, y) }?.let { return it.key }
        return null
    }

    private fun actionAt(x: Float, y: Float): (() -> Unit)? = rects.firstOrNull { it.action != null && it.rect.contains(x, y) }?.action
    private fun dp(v: Float): Float = v * resources.displayMetrics.density
}
