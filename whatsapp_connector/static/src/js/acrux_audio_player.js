odoo.define('whatsapp_connector.audio_player', function(require) {
"use strict";

var Widget = require('web.Widget')
var core = require('web.core')
var session = require('web.session')

var _t = core._t

/**
 * Es el reproductor de audios de chatroom
 *
 * @class
 * @name Message
 * @extends web.Widget
 */
var AudioPlayer = Widget.extend({
    template: 'acrux_audio_player',
    events: {
        'loadeddata audio': 'onLoadData',
        'error audio': 'onError',
        'timeupdate audio': 'onTimeUpdate',
        'ended audio': 'onEnded',
        'click .play > a': 'onPlayPause',
        'click .progress': 'changeProgress',
        'click .download': 'onDownload',
    },
    
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments)

        this.parent = parent
        this.options = _.extend({}, options)
        this.context = _.extend({}, this.parent.context || {}, this.options.context)
        this.src = options.src
        this.ignoreTimeUpdateEvent = false
    },

    /**
     * @override
     * @see Widget.willStart
     */
    willStart: function() {
        return this._super().then(() => {
            if (this.promise) {  // no deberia pasar pero por si acaso.
                this.resolve()
            }
            this.promise = new Promise(resolve => this.resolve = resolve)
        })
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super().then(() => this._initRender())
    },

    /**
     * Hace trabajos de render
     *
     * @private
     * @returns {Promise} Para indicar que termino
     */
    _initRender: function() {
        let out = Promise.resolve()
        this.$player = this.$('.o_acrux_audio_player')
        this.$audio = this.$('audio')
        this.audio_obj = this.$audio ? this.$audio[0] : {}
        this.$progress = this.$player.find('.progress')
        this.$time = this.$player.find('.time')
        this.$progress_play = this.$progress.find('.playback')
        this.$player_play = this.$player.find('.play > a')
        this.$player.addClass('o_hidden')
        Object.keys(this.events).forEach(key => {
            if (key.includes('audio')) {
                const str = key.split(' ')
                this.$audio.on(str[0], this[this.events[key]].bind(this))
            }
        })
        if (this.src) {
            out = this.promise
            this.$audio[0].load()
            setTimeout(() => {
                if (this.promise) {
                    this.resolve()
                    this.promise = null
                }
            }, 2000)  // si no se carga entonces se libera el renderizado
        }
        return out
    },

    /**
     * @override
     * @see Widget.destroy
     */
    destroy: function() {
        if (this.$audio) {
            Object.keys(this.events).forEach(key => {
                if (key.includes('audio')) {
                    const str = key.split(' ')
                    this.$audio.off(str[0])
                }
            })
        }
        if (this.promise) {
            this.resolve()
            this.promise = null
        }
        this._super()
    },

    /**
     * Modifica la fuente del audio
     */
    setAudio: function(audio) {
        this.src = audio
    },

    /**
     * Cuando el audio termina de cargar
     */
    onLoadData: function(event) {
        const audio = event.target
        this.$player.removeClass('o_hidden')
        this.$time.html(this.calculateTime(audio.duration))
        this.resolve()
        this.promise = null
    },

    /**
     * Cuando hubo un error cargando el audio
     */
    onError: function() {
        this.$player.html(_t('Audio not found'))
        this.$player.removeClass('o_acrux_audio_player')
        this.$player.removeClass('o_hidden')
        this.resolve()
        this.promise = null
    },

    /**
     * Cuando se esta reproduciendo el audio
     */
    onTimeUpdate: function(event) {
        const audio = event.target
        let percentage = audio.currentTime * 100.00 / audio.duration
        percentage = Math.round(percentage)
        this.$progress_play.width(percentage + '%')
        if (!this.ignoreTimeUpdateEvent) {
            this.$time.html(this.calculateTime(audio.currentTime))
        }
    },

    /**
     * Cuando termino de reproducir el audio
     */
    onEnded: function(event) {
        this.ignoreTimeUpdateEvent = true
        const audio = event.target
        audio.currentTime = 0
        this.$player_play.html('▶')
        this.$time.html(this.calculateTime(audio.duration))
    },

    /**
     * Reproducir y pausar el audio 
     */
    onPlayPause: function(event) {
        event.preventDefault();
        this.ignoreTimeUpdateEvent = false
        if (this.audio_obj.paused) {
            this.audio_obj.play()
            $(event.target).html('⏸️')
        } else {
            this.audio_obj.pause()
            $(event.target).html('▶')
        }
    },

    /**
     * Cuando se cambia la posicion del audio, adelantar o retrazar.
     */
    changeProgress: function(event) {
        // clic en la barra de progreso del audio
        this.ignoreTimeUpdateEvent = false
        let relative_position, percentage
        relative_position = event.pageX - this.$progress.offset().left
        percentage = relative_position / this.$progress.outerWidth()
        if (Number.isFinite(this.audio_obj.duration)) {
            this.audio_obj.currentTime = this.audio_obj.duration * percentage
        }
    },

    /**
     * Transforma una cantidad de segundos a hora y minutos
     *
     * @param {Number} num Cantidad de segundo
     * @returns {String}
     */
    calculateTime: function (num) {
        let out = ''
        if (!isNaN(num) && Number.isFinite(num)) {
            let zero = (x) => x < 10 ? '0' + x : x;
            let minutes = Math.floor(num / 60.0);
            let seconds = Math.round(num) % 60;
            let hours = Math.floor(minutes / 60.0);
            minutes = Math.round(minutes) % 60;
    
            if (hours) {
                out = zero(hours) + ":";
            }
            out += zero(minutes) + ":" + zero(seconds);
        }
        return out;
    },

    /**
     * Descarga el audio.
     */
    onDownload: function() {
        if (this.src) {
            if (this.src.startsWith('blob:')) {
                const link = document.createElement('a')
                link.href = this.src
                link.download = 'audio.oga'
                link.click()
            } else {
                window.location = session.url(this.src, {download: true})
            } 
        }
    }
})

return AudioPlayer
})

