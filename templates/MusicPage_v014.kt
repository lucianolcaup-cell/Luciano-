package dev.limitedio.pipetv.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import dev.limitedio.pipetv.Bg
import dev.limitedio.pipetv.data.Item
import dev.limitedio.pipetv.data.Store
import dev.limitedio.pipetv.data.Yt
import dev.limitedio.pipetv.i18n.S
import dev.limitedio.pipetv.media.Session
import dev.limitedio.pipetv.ui.input.Keyboard
import dev.limitedio.pipetv.ui.input.Voice
import dev.limitedio.pipetv.ui.search.VoiceOrb

/** Vórtice Music: TV-first search, voice search, genres and ad-free audio playback. */
class MusicPage(c: Context) : ViewGroup(c) {
    private val filters = listOf("music_songs", "music_videos", "music_albums", "music_playlists")
    private fun typeNames() = if (S.cur.code == "pt") listOf("Músicas", "Clipes", "Álbuns", "Playlists") else listOf("Songs", "Videos", "Albums", "Playlists")
    private fun defaultQueries() = if (S.cur.code == "pt") listOf("músicas em alta Brasil", "clipes oficiais Brasil", "lançamentos musicais Brasil", "playlists hits Brasil") else listOf("top songs", "official music videos", "new music releases", "top music playlists")
    private fun genreNames() = if (S.cur.code == "pt") listOf("Pop", "Sertanejo", "Rock", "Gospel", "MPB", "Pagode", "Eletrônica", "Rap / Hip-Hop") else listOf("Pop", "Country", "Rock", "Gospel", "Brazilian", "Samba", "Electronic", "Rap / Hip-Hop")
    private fun genreQueries() = if (S.cur.code == "pt") listOf("pop Brasil", "sertanejo", "rock Brasil", "gospel Brasil", "MPB", "pagode", "música eletrônica", "rap hip hop Brasil") else listOf("pop", "country", "rock", "gospel", "brazilian music", "samba", "electronic music", "rap hip hop")

    var onVoice: () -> Unit = {}
    private var heading = if (S.cur.code == "pt") "Em alta agora" else "Trending now"
    val grid = Grid(c) { heading }.apply { upExit = true }
    private val search = MusicSearchBar(c)
    private val types = MusicTypeBar(c) { typeNames() }
    private val genres = MusicGenreBar(c) { genreNames() }
    private val keyboard = Keyboard(c).apply { visibility = GONE }
    private val orb = VoiceOrb(c).apply { visibility = GONE }

    private var zone = 0
    private var loaded = false
    private var enabled = true
    private var request = 0

    private val titlePaint = Ui.paint(Ui.TEXT, 45f, true)
    private val subPaint = Ui.paint(Ui.DIM, 22f)
    private val badgeText = Ui.paint(0xFF071018.toInt(), 18f, true)
    private val glow = Paint(Paint.ANTI_ALIAS_FLAG)
    private val badge = Paint(Paint.ANTI_ALIAS_FLAG)
    private val rr = RectF()

    init {
        setWillNotDraw(false)
        listOf<View>(search, types, genres, grid, keyboard, orb).forEach(::addView)
        types.onChange = { loadDefault(it) }
        genres.onPick = { i ->
            search.query = ""; search.invalidate()
            heading = genreNames()[i]
            load(genreQueries()[i], "music_songs")
            setZone(3)
        }
        grid.onRetry = { if (search.query.isBlank()) loadDefault(types.sel) else runSearch(search.query) }
        keyboard.onKey = { key ->
            when (key) {
                "@space" -> edit(" ")
                "@del" -> setQuery(search.query.dropLast(1))
                "@clear" -> setQuery("")
                "@go" -> if (search.query.isNotBlank()) { closeKeyboard(); runSearch(search.query) }
                "@mic" -> onVoice()
                else -> edit(key)
            }
        }
    }

    fun picks(pick: (Item) -> Unit, menu: (Item) -> Unit) {
        grid.onPick = { item -> Session.armMusic(); pick(item) }
        grid.onMenu = menu
    }

    fun enter() {
        bindVoice(); setZone(0)
        if (!loaded) { loaded = true; loadDefault(types.sel) }
    }

    fun reset() { loaded = false; setQuery(""); loadDefault(types.sel) }

    private fun bindVoice() {
        Voice.onResult = { spoken -> post { setQuery(spoken); closeKeyboard(); runSearch(spoken) } }
        Voice.onState = {
            search.listening = Voice.active
            keyboard.listening = Voice.active
            orb.visibility = if (Voice.active) VISIBLE else GONE
            search.invalidate(); keyboard.invalidate(); orb.invalidate()
        }
    }

    private fun edit(s: String) = setQuery(search.query + s)
    private fun setQuery(q: String) {
        search.query = q; keyboard.text = q
        search.invalidate(); keyboard.invalidate()
    }

    private fun openKeyboard() {
        keyboard.visibility = VISIBLE
        types.visibility = GONE; genres.visibility = GONE; grid.visibility = GONE
        setZone(4); relayout()
    }

    private fun closeKeyboard() {
        keyboard.visibility = GONE
        types.visibility = VISIBLE; genres.visibility = VISIBLE; grid.visibility = VISIBLE
        setZone(0); relayout()
    }

    private fun runSearch(raw: String) {
        val q = raw.trim(); if (q.isEmpty()) return
        heading = if (S.cur.code == "pt") "Resultados para “$q”" else "Results for “$q”"
        load(q, filters[types.sel]); setZone(3)
    }

    private fun loadDefault(i: Int) {
        heading = if (S.cur.code == "pt") "${typeNames()[i]} em destaque" else "Featured ${typeNames()[i]}"
        load(defaultQueries()[i], filters[i])
    }

    private fun load(query: String, filter: String) {
        val t = ++request
        grid.items = emptyList(); grid.message = null; grid.busy = true; grid.invalidate()
        Bg.io({ Yt.search(query, filter).items }) { result ->
            if (t != request) return@io
            val seen = Store.entries().associate { e -> e.item.id to e.fraction }
            val items = (result ?: emptyList()).onEach { it.progress = seen[it.id] ?: 0f }
            grid.message = when {
                result == null -> if (S.cur.code == "pt") "Não foi possível carregar o Vórtice Music." else "Couldn't load Vórtice Music."
                items.isEmpty() -> if (S.cur.code == "pt") "Nenhum resultado musical." else "No music results."
                else -> null
            }
            grid.items = items; grid.busy = false; grid.invalidate()
        }
    }

    fun lit(v: Boolean) { enabled = v; setZone(zone) }

    fun back(): Boolean {
        if (Voice.active) { Voice.stop(); return true }
        if (zone == 4) { closeKeyboard(); return true }
        if (zone == 3) { setZone(2); return true }
        return false
    }

    fun key(code: Int): Boolean = when (zone) {
        0 -> when (code) {
            KeyEvent.KEYCODE_DPAD_LEFT -> { search.micFocus = false; search.invalidate(); true }
            KeyEvent.KEYCODE_DPAD_RIGHT -> { search.micFocus = true; search.invalidate(); true }
            KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> { if (search.micFocus) onVoice() else openKeyboard(); true }
            KeyEvent.KEYCODE_DPAD_DOWN -> { setZone(1); true }
            else -> false
        }
        1 -> types.key(code) || when (code) {
            KeyEvent.KEYCODE_DPAD_UP -> { setZone(0); true }
            KeyEvent.KEYCODE_DPAD_DOWN -> { setZone(2); true }
            else -> false
        }
        2 -> genres.key(code) || when (code) {
            KeyEvent.KEYCODE_DPAD_UP -> { setZone(1); true }
            KeyEvent.KEYCODE_DPAD_DOWN -> { setZone(3); true }
            else -> false
        }
        3 -> grid.key(code) || (code == KeyEvent.KEYCODE_DPAD_UP).also { if (it) setZone(2) }
        else -> keyboard.key(code)
    }

    private fun setZone(z: Int) {
        zone = z
        search.lit = enabled && z == 0
        types.lit = enabled && z == 1
        genres.lit = enabled && z == 2
        grid.lit = enabled && z == 3
        keyboard.lit = enabled && z == 4
        search.invalidate(); types.invalidate(); genres.invalidate(); grid.invalidate(); keyboard.invalidate()
    }

    private fun relayout() = onLayout(true, left, top, right, bottom)

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        glow.shader = LinearGradient(0f, 0f, width * .72f, Ui.u(180), Ui.ACCENT2, 0x00000000, Shader.TileMode.CLAMP)
        glow.alpha = 42; c.drawRect(0f, 0f, width.toFloat(), Ui.u(180), glow)
        Txt.draw(c, "Vórtice Music", Ui.u(32), Ui.u(58), width - Ui.u(64), titlePaint)
        val sub = if (S.cur.code == "pt") "Artistas, músicas, álbuns e gêneros · pesquisa por voz" else "Artists, songs, albums and genres · voice search"
        Txt.draw(c, sub, Ui.u(34), Ui.u(92), width - Ui.u(250), subPaint)
        rr.set(width - Ui.u(204), Ui.u(28), width - Ui.u(34), Ui.u(70))
        badge.shader = LinearGradient(rr.left, 0f, rr.right, 0f, Ui.ACCENT, Ui.ACCENT2, Shader.TileMode.CLAMP)
        c.drawRoundRect(rr, rr.height()/2, rr.height()/2, badge)
        Txt.draw(c, if (S.cur.code == "pt") "SEM ANÚNCIOS" else "AD-FREE", rr.left, rr.centerY() + Ui.u(7), rr.width(), badgeText, true)
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val w = r - l; val h = b - t
        search.layout(0, Ui.u(105).toInt(), w, Ui.u(182).toInt())
        if (keyboard.visibility == VISIBLE) keyboard.layout(0, Ui.u(182).toInt(), w, h)
        else {
            types.layout(0, Ui.u(187).toInt(), w, Ui.u(252).toInt())
            genres.layout(0, Ui.u(258).toInt(), w, Ui.u(390).toInt())
            grid.layout(0, Ui.u(395).toInt(), w, h)
        }
        orb.layout(0, 0, w, h)
    }
}

private class MusicSearchBar(c: Context) : AnimView(c) {
    var query = ""; var lit = false; var micFocus = false; var listening = false
    private val face = Ui.paint(Ui.SURFACE); private val text = Ui.paint(Ui.TEXT, 27f, true); private val hint = Ui.paint(Ui.DIM, 26f); private val ico = Ui.paint(Ui.TEXT)
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG); private val r = RectF()
    override fun render(c: Canvas, dt: Float) {
        val side = Ui.u(32); val gap = Ui.u(12); val micW = Ui.u(76); val mainRight = width - side - micW - gap
        r.set(side, Ui.u(7), mainRight, height - Ui.u(7)); c.drawRoundRect(r, Ui.u(22), Ui.u(22), face)
        if (lit && !micFocus) { ring.style = Paint.Style.STROKE; ring.strokeWidth = Ui.u(4); ring.shader = LinearGradient(r.left,0f,r.right,0f,Ui.ACCENT,Ui.ACCENT2,Shader.TileMode.CLAMP); c.drawRoundRect(r,Ui.u(22),Ui.u(22),ring); ring.style = Paint.Style.FILL }
        ico.color = Ui.DIM; Icons.draw(c, Icons.SEARCH, r.left + Ui.u(29), r.centerY(), Ui.u(17), ico)
        val label = if (query.isBlank()) (if (S.cur.code == "pt") "Pesquisar artista, música ou álbum" else "Search artist, song or album") else query
        val p = if (query.isBlank()) hint else text
        Txt.draw(c, Txt.fit(p, label, r.width()-Ui.u(76)), r.left+Ui.u(56), r.centerY()+Ui.u(9), r.width()-Ui.u(70), p)
        r.set(width-side-micW, Ui.u(7), width-side, height-Ui.u(7))
        if (lit && micFocus) { ring.shader = LinearGradient(r.left,0f,r.right,r.bottom,Ui.ACCENT,Ui.ACCENT2,Shader.TileMode.CLAMP); c.drawRoundRect(r,Ui.u(22),Ui.u(22),ring) } else c.drawRoundRect(r,Ui.u(22),Ui.u(22),face)
        ico.color = if (listening) Ui.ACCENT2 else Ui.TEXT; Icons.draw(c, Icons.MIC, r.centerX(), r.centerY(), Ui.u(19), ico)
    }
}

private class MusicTypeBar(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel = 0; private set; var lit = false; var onChange: (Int) -> Unit = {}
    private val text = Ui.paint(Ui.TEXT, 23f, true); private val face = Ui.paint(Ui.SURFACE); private val fill = Paint(Paint.ANTI_ALIAS_FLAG); private val r = RectF()
    fun key(code: Int): Boolean { val d = when(code){KeyEvent.KEYCODE_DPAD_LEFT->-1;KeyEvent.KEYCODE_DPAD_RIGHT->1;else->return false}; val n=sel+d; if(n !in 0..3)return false; sel=n; onChange(n); invalidate(); return true }
    override fun render(c: Canvas, dt: Float) { val pad=Ui.u(32); val w=(width-pad*2)/4f; labels().forEachIndexed{i,label-> val x=pad+i*w; r.set(x+Ui.u(5),Ui.u(6),x+w-Ui.u(5),height-Ui.u(6)); if(i==sel&&lit){fill.shader=LinearGradient(r.left,0f,r.right,0f,Ui.ACCENT,Ui.ACCENT2,Shader.TileMode.CLAMP);c.drawRoundRect(r,r.height()/2,r.height()/2,fill)}else c.drawRoundRect(r,r.height()/2,r.height()/2,face); text.color=if(i==sel&&lit)0xFF0A0B14.toInt() else Ui.TEXT; Txt.draw(c,label,r.left,r.centerY()+Ui.u(8),r.width(),text,true)} }
}

private class MusicGenreBar(c: Context, private val labels: () -> List<String>) : AnimView(c) {
    var sel=0; private set; var lit=false; var onPick:(Int)->Unit={}
    private val text=Ui.paint(Ui.TEXT,21f,true); private val face=Ui.paint(Ui.SURFACE); private val fill=Paint(Paint.ANTI_ALIAS_FLAG); private val r=RectF()
    fun key(code:Int):Boolean { val row=sel/4; val col=sel%4; val n=when(code){KeyEvent.KEYCODE_DPAD_LEFT->if(col>0)sel-1 else return false;KeyEvent.KEYCODE_DPAD_RIGHT->if(col<3)sel+1 else return false;KeyEvent.KEYCODE_DPAD_UP->if(row>0)sel-4 else return false;KeyEvent.KEYCODE_DPAD_DOWN->if(row<1)sel+4 else return false;KeyEvent.KEYCODE_DPAD_CENTER,KeyEvent.KEYCODE_ENTER->{onPick(sel);return true};else->return false}; sel=n;invalidate();return true }
    override fun render(c:Canvas,dt:Float){val pad=Ui.u(32);val gap=Ui.u(10);val cw=(width-pad*2-gap*3)/4f;val ch=(height-gap)/2f;labels().forEachIndexed{i,label->val row=i/4;val col=i%4;val x=pad+col*(cw+gap);val y=row*(ch+gap);r.set(x,y+Ui.u(2),x+cw,y+ch-Ui.u(2));if(lit&&i==sel){fill.shader=LinearGradient(r.left,r.top,r.right,r.bottom,Ui.ACCENT,Ui.ACCENT2,Shader.TileMode.CLAMP);c.drawRoundRect(r,Ui.u(18),Ui.u(18),fill)}else c.drawRoundRect(r,Ui.u(18),Ui.u(18),face);text.color=if(lit&&i==sel)0xFF0A0B14.toInt() else Ui.TEXT;Txt.draw(c,label,r.left+Ui.u(8),r.centerY()+Ui.u(8),r.width()-Ui.u(16),text,true)}}
}
