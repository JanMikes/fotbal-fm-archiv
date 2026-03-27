/**
 * eSports.cz [www.esports.cz] Media Gallery
 * Bitbucket:       https://bitbucket.org/esportscz/esgallery
 * Description:     Responsive Media Gallery with video and audio play.
 * Version:         1.9.5 (20140524)
 * Author:          Tomas Novosad [tomas.novosad@esports.cz]
 * Dependences:     jQuery 1.8.3 [http://jquery.com/]
 *                  jQuery Tiny Scrollbar [http://baijs.nl/tinyscrollbar/]
 *                  jQuery Mouse Wheel [http://brandonaaron.net/code/mousewheel/demos]
 *                  spin.js [http://fgnass.github.com/spin.js/]
 *                  JW Player 5.10 [http://www.longtailvideo.com/jw-player/]
 *                  jQuery++ event.swipe [http://jquerypp.com/#swipe]
 *                  ZeroClipboard [https://github.com/jonrohan/ZeroClipboard]
 */

(function ( $ ) {

	$.fn.esgallery = function(options) {

		var esg = $.fn.esgallery;

		esg.defaults = {
			    path                      : 'esGallery/'
			,	container                 : 'esgallery'
			,	containerOverlay          : 'esgallery-overlay'
			,	sprite                    : 'sprite'
			,	onReady					  : false
			,	controlCaption            : true
			,	controlPlaylist           : true
			,	controlSlideshow          : true
			,	controlFullImage          : false
            ,	controlTitle              : false
			,	social                    : false
			,	summary					  : false
			,	htmlMediaPlaylist         : '#media-playlist'
			,	htmlMediaControl          : '#media-control'
			,	htmlMediaControlContainer : '#media-control-container'
			,	htmlMediaList             : this.selector
			,	htmlMediaMainContainer    : '#media-main-container'
			,	htmlMediaCaption          : '#media-caption'
			,	htmlMediaContainer        : '#media-container'
			,	htmlMediaContent          : '#media-content'
			,	htmlMediaMain             : '#media-main'
			,	htmlMediaImage            : '#media-image'
			,	htmlMediaVideo            : '#media-video'
			,	htmlMediaTop              : '#media-top'
            ,	htmlMediaSocial           : '#media-socials'
			,	htmlMediaSummary          : '#media-summary-list'
            ,	htmlMediaLink             : '#media-link'
            ,	htmlMediaLinkUrl          : '#media-link-url'
            ,	htmlMediaLinkCopy         : '#media-link-copy'
            ,   htmlMediaLinkCopyHover    : 'hover'
			,	htmlCaptionContent        : '.caption-content'
			,	htmlCaptionText           : '.caption-text'
			,	htmlControlCaption        : '.control-caption'
			,	htmlControlPlaylist       : '.control-playlist'
			,	htmlControlSlideshow      : '.control-slideshow'
            ,	htmlControlFullImage      : '.control-full-image'
			,	htmlControlIco            : '.ico'
			,	htmlOpenLink              : '.esgallery-open'
			,	htmlCloseLink             : '.esgallery-close'
			,	htmlSummaryLink           : '.esgallery-summary'
			,	htmlPrevLink              : '#prev'
			,	htmlNextLink              : '#next'
			,	htmlArrow                 : '.arrow'
			,	htmlLeft                  : '.left'
			,	htmlRight                 : '.right'
			,	htmlGlow                  : '.glow'
			,	htmlError                 : '.error'
			,	htmlActive                : '.active'
			,	htmlActiveControl         : '.active-control'
			,	htmlBodyLock              : '.esgallery-lock'
			,	htmlStopSlideshow         : '.stop-slideshow'
            ,   showLink                  : '#show-link'
            ,   showLinkCopy              : 'Kopírovat odkaz'
			,   facebookLink              : '#facebook'
			,   twitterLink               : '#twitter'
			,   gplusLink                 : '#gplus'
            ,   facebookSharer	          : 'http://www.facebook.com/sharer.php?u='
            ,   twitterSharer	          : 'http://www.twitter.com/share?url='
            ,   gplusSharer 	          : 'http://plus.google.com/share?url='
            ,   newWindowWidth 	          : '700'
            ,   newWindowHeight 	      : '450'
            ,   zeroClipboardJs	          : 'esgallery/assets/ZeroClipboard/ZeroClipboard.min.js'
            ,   zeroClipboardSwf          : 'esgallery/assets/ZeroClipboard/ZeroClipboard.swf'
            ,   jwplayerJs     	          : 'esgallery/assets/jwplayer/jwplayer.js'
            ,   jwplayerSwf  	          : 'esgallery/assets/jwplayer/player.swf'
		};

		esg.o               = $.extend(esg.defaults, options);
        esg.b               = $('body');
		esg.lockGlow        = false;
		esg.lockMedia       = false;
		esg.isSlideshow     = false;
		esg.captionHide     = false;
		esg.isIE8           = false;
		esg.mediaType       = "image";
		esg.videoRender     = "flash";
		esg.hash            = '';
		esg.mediaListParent = $(esg.o.htmlMediaList).parent();
		esg.mediaTopParent  = $(esg.o.htmlMediaTop).parent();
        esg.screenX         = screen.width/2 - esg.o.newWindowWidth/2;
        esg.screenY         = screen.height/2 - esg.o.newWindowHeight/2;



		/* ==================================================================================================================================
		 *  HTML manipulate
		 *  ================================================================================================================================== */

		esg.htmlWrapper = function () {
			var controlElementsWidth = 0;

			esg.b.addClass(esg.getName(esg.o.htmlBodyLock));
			esg.b.append('<div class="' + esg.o.container + '"></div>');
			esg.p = $('.' + esg.o.container);
			$(esg.p).show();
			$(esg.p).wrap('<div class="' + esg.o.containerOverlay + ' ' + esg.o.sprite + '" />');
            $(esg.o.htmlMediaMainContainer).append('<div id="' + esg.getName(esg.o.htmlMediaLink) + '" class="' + esg.o.sprite + '"></div>');
			$(esg.o.htmlMediaList).show();
			$(esg.o.htmlMediaList).addClass('overview');
			$(esg.o.htmlMediaList).wrap('<div class="viewport"></div>');
			$(".viewport").after('<div class="scrollbar"><div class="track"><div class="thumb"><div class="corner"></div><div class="main"></div><div class="corner"></div></div></div></div>');
			$(".viewport, .scrollbar").wrapAll('<div id="' + esg.getName(esg.o.htmlMediaPlaylist) + '" class="' + esg.o.sprite + '" />');
			$(esg.o.htmlMediaPlaylist).before('<div id="' + esg.getName(esg.o.htmlMediaMainContainer) + '"><div class="' + esg.getName(esg.o.htmlArrow) + ' ' + esg.getName(esg.o.htmlLeft) + '"><a href="#" id="' + esg.getName(esg.o.htmlPrevLink) + '" class="' + esg.o.sprite + '"><span class="' + esg.getName(esg.o.htmlGlow) + ' ' + esg.o.sprite + '">&nbsp;</span></a></div><div id="' + esg.getName(esg.o.htmlMediaMain) + '"><div id="' + esg.getName(esg.o.htmlMediaContent) + '"></div></div><div class="' + esg.getName(esg.o.htmlArrow) + ' ' + esg.getName(esg.o.htmlRight) + '"><a href="#" id="' + esg.getName(esg.o.htmlNextLink) + '" class="' + esg.o.sprite + '"><span class="' + esg.getName(esg.o.htmlGlow) + ' ' + esg.o.sprite + '">&nbsp;</span></a></div></div>');
			$(esg.o.htmlMediaMainContainer + ', ' + esg.o.htmlMediaPlaylist).wrapAll('<div id="' + esg.getName(esg.o.htmlMediaContainer) + '" />');
			$(esg.o.htmlMediaMainContainer).append('<div id="' + esg.getName(esg.o.htmlMediaSummary) + '" />');
			if (!esg.o.summary) $(esg.o.htmlMediaSummary).addClass('hide');
			$(esg.o.htmlMediaContent).append('<div id="' + esg.getName(esg.o.htmlMediaCaption) + '" />');
			$(esg.o.htmlMediaCaption).append('<div class="' + esg.getName(esg.o.htmlCaptionContent) + '"><div class="' + esg.getName(esg.o.htmlCaptionText) + '"></div><div class="clear">&nbsp;</div></div>');
			$(esg.o.htmlMediaPlaylist).before('<div id="' + esg.getName(esg.o.htmlMediaControl) + '" />');
			$(esg.o.htmlMediaControl).append('<div id="' + esg.getName(esg.o.htmlMediaControlContainer) + '" />');
			if (esg.o.controlCaption) $(esg.o.htmlMediaControlContainer).append('<a href="#" class="' + esg.getName(esg.o.htmlControlCaption) + '"><span class="' + esg.getName(esg.o.htmlControlIco) + ' ' + esg.o.sprite + '"></span></a> ');
			if (esg.o.controlPlaylist) $(esg.o.htmlMediaControlContainer).append('<a href="#" class="' + esg.getName(esg.o.htmlControlPlaylist) + '"><span class="' + esg.getName(esg.o.htmlControlIco) + ' ' + esg.o.sprite + '"></span></a> ');
            if (esg.o.controlFullImage) $(esg.o.htmlMediaControlContainer).append('<a href="#" class="' + esg.getName(esg.o.htmlControlFullImage) + '"><span class="' + esg.getName(esg.o.htmlControlIco) + ' ' + esg.o.sprite + '"></span></a> ');
            if (esg.o.controlSlideshow) $(esg.o.htmlMediaControlContainer).append('<a href="#" class="' + esg.getName(esg.o.htmlControlSlideshow) + '"><span class="' + esg.getName(esg.o.htmlControlIco) + ' ' + esg.o.sprite + '"></span></a> ');
			if (!esg.o.controlTitle) $(esg.o.htmlMediaControlContainer + ' a ').width($(esg.o.htmlMediaControlContainer + ' > a > ' + esg.o.htmlControlIco).width()).addClass('no-text');
			$(esg.o.htmlMediaControlContainer + ' > *').each(function() {controlElementsWidth+= $(this).outerWidth(true);});
			$(esg.o.htmlMediaControlContainer).width(controlElementsWidth+6);
			$(esg.o.htmlMediaList + ' ul li').each(function(index) {$(this).attr("name", (index + 1));});
			$(esg.o.htmlMediaTop).show();
			$(esg.o.htmlMediaTop).appendTo('.' + esg.o.container);
			$(esg.o.htmlMediaContainer).appendTo('.' + esg.o.container);
            $(esg.o.htmlMediaMainContainer).append('<div id="' + esg.getName(esg.o.htmlMediaLink) + '" class="' + esg.o.sprite + '"></div>');
            $(esg.o.htmlMediaLink).append('<div id="' + esg.getName(esg.o.htmlMediaLinkUrl) + '"></div>');
            $(esg.o.htmlMediaLink).append('<div id="' + esg.getName(esg.o.htmlMediaLinkCopy) + '" data-clipboard-target="' + esg.getName(esg.o.htmlMediaLinkUrl) + '">' + esg.o.showLinkCopy + '</div>');
			$(esg.o.htmlMediaList + ' ul').clone().appendTo(esg.o.htmlMediaSummary);
			return true;
		};

		esg.htmlDeWrapper = function () {
			$(esg.p).hide();
			$(esg.o.htmlMediaTop).appendTo(esg.mediaTopParent);
			$(esg.o.htmlMediaList).appendTo(esg.mediaListParent);
			$(esg.o.htmlMediaContainer).remove();
			$('.' + esg.o.containerOverlay).remove();
			$(esg.o.htmlMediaList).hide();
			$('body').removeClass(esg.getName(esg.o.htmlBodyLock));
			$(esg.p).removeClass(esg.o.container);
			$(esg.o.htmlMediaTop).hide();
			return true;
		};

		/**
		 * Count height of #media-main-container.
		 * @return {int}
		 */
		esg.getMediaMainContainerHeight = function () {
			var mediaPlaylistHeight = 0;
			var mediaControlHeight  = 0;
			var otherElementsHeight = 0;
			if (($(esg.o.htmlMediaPlaylist).css('display') == "none") || ($(esg.o.htmlMediaPlaylist).attr('display') == "none")) {
				mediaPlaylistHeight = 0;
			} else {
				mediaPlaylistHeight = $(esg.o.htmlMediaPlaylist).height();
			}
			if (($(esg.o.htmlMediaControl).css('display') == "none") || ($(esg.o.htmlMediaControl).attr('display') == "none")) {
				mediaControlHeight = 0;
			} else {
				mediaControlHeight = $(esg.o.htmlMediaControl).outerHeight(true);
			}
			if ($(esg.o.htmlMediaTop).height() > 0) {
				otherElementsHeight+= $(esg.o.htmlMediaTop).height();
			}
			if (esg.mediaType == "video") {
				otherElementsHeight+= $(esg.o.htmlMediaCaption).height();
			}
			return (((esg.getDocumentHeight() - mediaPlaylistHeight) - mediaControlHeight) - otherElementsHeight);
		};

		/**
		 * @return {int}
		 */
		esg.getDocumentWidth = function() {
			return $(esg.p).width();
		};

		/**
		 * @return {int}
		 */
		esg.getDocumentHeight = function() {
			return $(esg.p).height();
		};

		/**
		 * Change dimension of some #media-content and children elements.
		 */
		esg.changeMediaContent = function() {
            var mediaElementWidth = 0;
            var mediaElementHeight = 0;
			$(esg.o.htmlMediaContent).width('100%');
			if (esg.mediaType == "image") {
				mediaElementWidth = $(esg.o.htmlMediaImage).width();
				mediaElementHeight = $(esg.o.htmlMediaImage).height();
			} else if (esg.mediaType == "video") {
				if (esg.videoRender == "flash") {
					mediaElementWidth = $(esg.o.htmlMediaVideo + '_wrapper').width();
					mediaElementHeight = $(esg.o.htmlMediaVideo + '_wrapper').height();
				} else if (esg.videoRender == "html5") {
					mediaElementWidth = $(esg.o.htmlMediaVideo).width();
					mediaElementHeight = $(esg.o.htmlMediaVideo).height();
				}
			}
			$(esg.o.htmlMediaTop).width(esg.getDocumentWidth());
			$(esg.o.htmlMediaContainer).width(esg.getDocumentWidth());
			$(esg.o.htmlMediaContainer).height(esg.getDocumentHeight());
			$(esg.o.htmlMediaContent).width(mediaElementWidth);
			$(esg.o.htmlMediaCaption).width(mediaElementWidth);
			if (esg.mediaType == "image") {
				$(esg.o.htmlMediaCaption).css('bottom', (($(esg.o.htmlMediaMain).height() - mediaElementHeight)/2));
			} else if (esg.mediaType == "video") {
				$(esg.o.htmlMediaCaption).css('bottom', (($(esg.o.htmlMediaMain).height() - mediaElementHeight)/2) - $(esg.o.htmlMediaCaption).height());
			}
		};

		esg.test = function() {
			$(esg.o.htmlMediaMainContainer + ', ' + esg.o.htmlMediaMain + ', ' + esg.o.htmlMediaContent).height(esg.getMediaMainContainerHeight());
		};

		/**
		 * Change dimension of some HTMLElements when the window change.
		 */
		esg.changeWindowSize = function() {
			var mediaMainContainerHeight = esg.getMediaMainContainerHeight();
			var windowWidth              = esg.getDocumentWidth();
			//var windowHeight             = esg.getDocumentHeight();
			var mediaPlaylistWidth       = 0;
			$(esg.o.htmlMediaList + ' ul li').each(function() {
				mediaPlaylistWidth += ($(this).outerWidth(true));
			});
			$(esg.o.htmlMediaMainContainer + ', ' + esg.o.htmlMediaMain + ', ' + esg.o.htmlMediaContent).height(mediaMainContainerHeight);
			$('.viewport').width(windowWidth);
			$('.overview').width(mediaPlaylistWidth);
			if (mediaPlaylistWidth < windowWidth) {
				$(esg.o.htmlMediaList).width(windowWidth);
			} else {
				$(esg.o.htmlMediaList).width(mediaPlaylistWidth);
			}
			esg.initScrollbar();
			esg.changeMediaContent();
			if ((esg.getDocumentHeight() < 640) && ($(esg.o.htmlMediaCaption).attr('class') != "hide")) {
				$(esg.o.htmlControlCaption).addClass(esg.getName(esg.o.htmlActiveControl));
				$(esg.o.htmlMediaCaption).addClass('hide');
				esg.captionHide = true;
			} else if ((esg.getDocumentHeight() > 640) && (esg.captionHide)) {
				$(esg.o.htmlControlCaption).removeClass(esg.getName(esg.o.htmlActiveControl));
				$(esg.o.htmlMediaCaption).removeClass('hide');
				esg.captionHide = false;
			}
			var thumbMainWidth = ($('.thumb').width() - ($('.corner').width()*2));
			$('.thumb > .main').width(thumbMainWidth);
		};



		/* ==================================================================================================================================
		 *  Spinner
		 *  ================================================================================================================================== */

        /**
         * @return {Object}
         */
        esg.initSpinner = function () {
            if (!esg.isIE8) {
                var opts = {
                    length: 12,
                    radius: 16,
                    color: '#fff',
                    className: 'spinner'
                };
                return Spinner(opts).spin(document.getElementById(esg.getName(esg.o.htmlMediaMain)));
            }
        };

        esg.stopSpinner = function (spinner) {
            if (!esg.isIE8) {
                spinner.stop();
            }
        };



		/* ==================================================================================================================================
		 *  Caption
		 *  ================================================================================================================================== */

        /**
         * @param {HTMLElement} el
         */
        esg.changeCaption = function (el) {
            var elementAttr = $(el).attr("alt");
            var elementSpan = $(el).parent().parent().children('div').html();
            var caption;
            if ((elementSpan !== undefined) && (elementSpan.length > 0)) {
                caption = elementSpan;
            } else if ((elementAttr !== undefined) && (elementAttr.length > 0)) {
                caption = '<div>' + elementAttr + '</div>';
            } else {
                caption = "";
            }
			if (esg.o.controlFullImage) {
				if ($(el).parent().attr("data-href-full")) {
					caption = caption + '<br><span class="link"><strong><a href="' + $(el).parent().attr("data-href-full") + '" target="_blank">Plná verze fotky</a></strong></span>';
				}
			}

			$(esg.o.htmlCaptionText).html(caption);
            if (caption.length > 0) {
                $(esg.o.htmlMediaCaption).height('auto');
            } else {
                $(esg.o.htmlMediaCaption).height('0');
            }
        };

        esg.hideCaption = function () {
            $(esg.o.htmlMediaCaption).hide();
        };

        esg.showCaption = function () {
            $(esg.o.htmlMediaCaption).fadeIn(300);
        };



		/* ==================================================================================================================================
		 *  Image
		 *  ================================================================================================================================== */

		/**
		 * @param {HTMLElement} el
		 */
		esg.changeImage = function(el) {
			var mediaMainContainerHeight = esg.getMediaMainContainerHeight();
			var imageHeight = 800;
			var imageVariant = el.attr('href');
			if (el.attr('data-href-exact')) {
				imageVariant = el.attr('data-href-exact').replace("exact", mediaMainContainerHeight);
			} else {
				if (mediaMainContainerHeight < 400) {
					imageHeight = 400;
				} else if (mediaMainContainerHeight < 600) {
					imageHeight = 600;
				} else if (mediaMainContainerHeight < 800) {
					imageHeight = 800;
				}
				if (el.attr('data-href-' + imageHeight)) imageVariant = el.attr('data-href-' + imageHeight);
			}
			if (!imageVariant.length) return false;
			var timeStamp = new Date().getTime();
			$(esg.o.htmlMediaContent).addClass('loading-' + timeStamp);
			esg.hideImage();
			esg.hideCaption();
			var img = $('<img />')
				.attr('src', imageVariant)
				.attr('id', esg.getName(esg.o.htmlMediaImage))
				.hide()
				.load(function() {
					esg.removeImage();
					esg.removeVideo();
					$(esg.o.htmlMediaContent).removeClass('loading-' + timeStamp);
					$(esg.o.htmlMediaContent).append(img);
					$(esg.o.htmlMediaImage).attr('alt', el.children().attr('alt'));
					esg.stopSpinner(spinner);
					$(esg.o.htmlMediaImage).fadeIn(300);
					setTimeout(function() {
						esg.test();
						esg.changeMediaContent();
						esg.changeCaption(el.children());
						esg.showCaption();
					}, 150);
				});
			setTimeout(function() {
				if ($('.loading-' + timeStamp).attr('id') == esg.getName(esg.o.htmlMediaContent)) {
					$(esg.o.htmlMediaMainContainer).width('100%');
					$(esg.o.htmlMediaMain).width('100%');
					$(esg.o.htmlMediaContent).width('100%');
					$(esg.o.htmlMediaContent).append('<span class="' + esg.getName(esg.o.htmlError) + '" />');
					esg.stopSpinner(spinner);
					$(esg.o.htmlMediaContent).removeClass('loading-' + timeStamp);
				}
			}, 15000);
            return true;
		};

		esg.hideImage = function() {
			$(esg.o.htmlMediaImage).hide();
		};

		esg.removeImage = function() {
			$(esg.o.htmlMediaImage).remove();
		};



		/* ==================================================================================================================================
		 *  Video
		 *  ================================================================================================================================== */

		/**
		 * @param {HTMLElement} el
		 */
		esg.changeVideo = function(el) {
			var videoHeight = 315;
			var videoWidth = 560;
			var videoImage = '';
            var videoFile = el.attr("href");
			var dataVideoHeight = el.attr("data-video-height");
			var dataVideoWidth = el.attr("data-video-width");
			var dataVideoImage = el.attr("data-video-image");
			esg.removeImage();
			esg.removeVideo();
			esg.hideCaption();
			esg.stopSpinner(spinner);
			if (dataVideoHeight > 0) videoHeight = dataVideoHeight;
			if (dataVideoWidth > 0) videoWidth = dataVideoWidth;
			if (dataVideoImage) videoImage = dataVideoImage;
            
            $("#" + esg.getName(esg.o.htmlMediaVideo)).remove();
            $(esg.o.htmlMediaContent).append('<div id="' + esg.getName(esg.o.htmlMediaVideo) + '"></div>');
            
            $(esg.o.htmlMediaContent).append('<script type="text/javascript" src="' + esg.o.jwplayerJs + '"></script>');  
            $(esg.o.htmlMediaContent).append("<script type='text/javascript'>jwplayer('" + esg.getName(esg.o.htmlMediaVideo) + "').setup({ 'base': '/inc/js/jw_player_6.11/', 'file': '" + videoFile + "', 'height': "+videoHeight+", 'width': "+videoWidth+", 'allowfullscreen': true, 'youtube.quality': 'highres', 'autostart': true, 'controlbar': 'over'});</script>");
            
			esg.changeCaption(el.children());
			esg.showCaption();
			jwplayer().onReady(
				function() {
					esg.videoRender = jwplayer().renderingMode;
					esg.test();
					esg.changeMediaContent();
				}
			);
		};

		esg.removeVideo = function() {
			if (esg.videoRender == "flash") {
				$(esg.o.htmlMediaVideo + '_wrapper').remove();
			} else if (esg.videoRender == "html5") {
				$(esg.o.htmlMediaVideo).remove();
			}
		};



		/* ==================================================================================================================================
		 *  Change media item
		 *  ================================================================================================================================== */
		/**
		 * @param {HTMLElement} el
		 * @param {HTMLElement} elNew
		 */
		esg.changeItem = function(el, elNew) {
			if (!esg.lockMedia) {
				esg.lockMedia = true;
				$(esg.o.htmlError).remove();
				$(esg.o.htmlMediaContent).removeClass();
				if (!$('.spinner').length) { //noinspection JSUndeclaredVariable
                    spinner = esg.initSpinner();
                }
				if (elNew.children().attr("data-media-type") == "video") {
					esg.mediaType = "video";
					if (esg.isSlideshow) esg.toggleSlideshow();
					esg.changeVideo(el);
                    if (esg.o.controlFullImage) esg.toggleFullImage(false);
				} else {
					esg.mediaType = "image";
					esg.changeImage(el);
                    if (esg.o.controlFullImage) {
                        if (elNew.children().attr("data-href-full")) {
                            esg.toggleFullImage(true, elNew.children().attr("data-href-full"));
                        } else {
                            esg.toggleFullImage(false);
                        }
                    }
				}
				esg.elNewName = $(elNew).attr('name');
				esg.checkFirstLast(esg.elNewName);
				esg.changePlaylistActive(esg.elNewName);
				esg.changeScrollbarPosition(el, esg.elNewName);
				esg.setHash(el);
				setTimeout(function() {
					esg.lockMedia = false;
				}, 500);
			}
		};



		/* ==================================================================================================================================
		 *  Scrollbar
		 *  ================================================================================================================================== */

		/**
		 * @param {number} shift
		 */
		esg.initScrollbar = function(shift) {
			var mediaScrollbar = $(esg.o.htmlMediaPlaylist);
			mediaScrollbar.tinyscrollbar({ axis: 'x'});
			if (shift > 0) mediaScrollbar.tinyscrollbar_update(shift);
		};

		/**
		 * Change scrollbar position look to active item in playlist.
		 * @param {HTMLElement} el
		 * @param {string} elNewName
		 */
		esg.changeScrollbarPosition = function(el, elNewName) {
			var elNew = $(esg.o.htmlMediaList + ' ul > li[name="' + elNewName + '"]');
			var position = elNew.position();
			var leftPositionItem = position.left + elNew.outerWidth(true);
			if (!esg.checkLast(elNew)) {
				leftPositionItem += el.parent().prev().outerWidth(true) ;
			}
			if ((!esg.checkLast(elNew)) && (!$(esg.o.htmlMediaList + ' > ul > li:last-child').prev().is(elNew))) {
				leftPositionItem += el.parent().prev().outerWidth(true);
			}
			var scrollbarPosition = leftPositionItem - esg.getDocumentWidth();
			esg.initScrollbar(scrollbarPosition);
		};

		/**
		 * Change scrollbar position look to active item in playlist.
		 */
		esg.scrollToActive = function() {
			var el = $(esg.o.htmlMediaList + ' ul > li' + esg.o.htmlActive);
			//var el = $(esg.o.htmlActive);
			var position = el.position();
			var leftPositionItem = position.left + el.outerWidth(true) ;
			if (!esg.checkLast(el.next())) {
				leftPositionItem += el.next().outerWidth(true);
			}
			if (!esg.checkLast(el.next().next())) {
				leftPositionItem += el.next().next().outerWidth(true);
			}
			var scrollbarPosition = leftPositionItem - esg.getDocumentWidth();
			esg.initScrollbar(scrollbarPosition);
		};



		/* ==================================================================================================================================
		 *  Move to next / previous item
		 *  ================================================================================================================================== */

		/**
		 * @param {Boolean} animate
		 */
		esg.moveNext = function(animate) {
			if (!esg.checkLast($(esg.o.htmlActive))) {
				var element = $(esg.o.htmlActive).next('li').children();
				var newActive = $(esg.o.htmlActive).next('li');
				esg.changeItem(element, newActive);
				if (animate == true) esg.animateArrow(esg.o.htmlNextLink, 'both');
			}
		};

		/**
		 * @param {Boolean} animate
		 */
		esg.movePrev = function(animate) {
			if (!esg.checkFirst($(esg.o.htmlActive))) {
				var element = $(esg.o.htmlActive).prev('li').children();
				var newActive = $(esg.o.htmlActive).prev('li');
				esg.changeItem(element, newActive);
				if (animate == true) esg.animateArrow(esg.o.htmlPrevLink, 'both');
			}
		};



		/* ==================================================================================================================================
		 *  Last / first item checking
		 *  ================================================================================================================================== */

		/**
		 * @param {HTMLElement} el
		 */
		esg.checkFirstLast = function(elNewName) {
			if ($('li[name="' + elNewName + '"]').is(":first-child")) {$(esg.o.htmlPrevLink).addClass('hidden');}else{$(esg.o.htmlPrevLink).removeClass('hidden');}
			if ($('li[name="' + elNewName + '"]').is(":last-child")) {$(esg.o.htmlNextLink).addClass('hidden');}else{$(esg.o.htmlNextLink).removeClass('hidden');}
		};

		/**
		 * @param {HTMLElement} el
		 * @return {Boolean}
		 */
		esg.checkFirst = function(el) {
			return ($(el).is(":first-child"));
		};

		/**
		 * @param {HTMLElement} el
		 * @return {Boolean}
		 */
		esg.checkLast = function(el) {
			return ($(el).is(":last-child"));
		};



		/* ==================================================================================================================================
		 *  Playlist manipulate
		 *  ================================================================================================================================== */

		/**
		 * @param {HTMLElement} el
		 */
		esg.changeDefaultItem = function(el) {
			esg.changeItem($(el), $(el).parent());
		};

		/**
		 * @param {HTMLElement} el
		 */
		esg.changeFromPlaylist = function(el) {
			esg.hideSummary();
			esg.changeItem($(el), $(el).parent());
		};

		/**
		 * @param {HTMLElement} el
		 */
		esg.changeFromSummary = function(el) {
			esg.hideSummary();
			esg.changeItem($(el), $(el).parent());
		};

		/**
		 * Set active element in playlist and summary list.
		 */
		esg.changePlaylistActive = function(elNewName) {
			$(esg.o.htmlMediaList + ' > ul > li').removeClass(esg.getName(esg.o.htmlActive));
			$(esg.o.htmlMediaSummary + ' > ul > li').removeClass(esg.getName(esg.o.htmlActive));
			$('li[name="' + elNewName + '"]').addClass(esg.getName(esg.o.htmlActive));
		};



		/* ==================================================================================================================================
		 *  Photos Summary
		 *  ================================================================================================================================== */

		esg.toggleSummary = function() {
			if (!esg.o.htmlMediaSummary) return false;
			if ($(esg.o.htmlMediaSummary).attr('class') == "hide") {
				$(esg.o.htmlMediaSummary).toggleClass('hide');
			} else {
				setTimeout(function() {$(esg.o.htmlMediaSummary).toggleClass('hide');}, 500);
			}
			return true;
		}

		esg.hideSummary = function() {
			if (!esg.o.htmlMediaSummary) return false;
			$(esg.o.htmlMediaSummary).addClass('hide');
			return true;
		}


		/* ==================================================================================================================================
		 *  User behavior
		 *  ================================================================================================================================== */

		esg.toggleCaption = function() {
			if (!esg.o.controlCaption) return false;
			$(esg.o.htmlMediaCaption).fadeToggle(400);
			if ($(esg.o.htmlMediaCaption).attr('class') == "hide") {
				$(esg.o.htmlMediaCaption).toggleClass('hide');
			} else {
				setTimeout(function() {$(esg.o.htmlMediaCaption).toggleClass('hide');}, 500);
			}
			$(esg.o.htmlControlCaption).toggleClass(esg.getName(esg.o.htmlActiveControl));
            return true;
		};

		esg.togglePlaylist = function() {
			if (!esg.o.controlPlaylist) return false;
			var mediaPlaylistHeight = ($(esg.o.htmlMediaPlaylist).outerHeight(true));
			if ($(esg.o.htmlMediaPlaylist).hasClass("hide")) {
				$(esg.o.htmlMediaPlaylist).toggleClass('hide');
				$(esg.o.htmlMediaPlaylist).slideDown(400);
				$(esg.o.htmlMediaControl).animate({
					bottom: '+=' + mediaPlaylistHeight
				}, 400);
			} else {
				$(esg.o.htmlMediaPlaylist).slideUp(400);
				setTimeout(function() {
					$(esg.o.htmlMediaPlaylist).toggleClass('hide');
				}, 400);
				$(esg.o.htmlMediaControl).animate({
					bottom: '-=' + mediaPlaylistHeight
				}, 400);
			}
			setTimeout(function() {
				esg.changeWindowSize();
				esg.scrollToActive();
				$(esg.o.htmlControlPlaylist).toggleClass(esg.getName(esg.o.htmlActiveControl));
			}, 400);
            return true;
		};

		esg.toggleSlideshow = function() {
			if (!esg.o.controlSlideshow) return false;
			if (esg.isSlideshow) {
				esg.isSlideshow = false;
			} else {
				esg.isSlideshow = true;
				esg.slideshow();
			}
			$(esg.o.htmlControlSlideshow).toggleClass(esg.getName(esg.o.htmlActiveControl));
            return true;
		};

		/**
         * @param {boolean} show
         * @param {string} url
         */
        esg.toggleFullImage = function(show, url) {
            if (!esg.o.htmlControlFullImage) return false;
            if (show) {
                if (url.length > 0) {
                    $(esg.o.htmlControlFullImage).show();
                    $(esg.o.htmlControlFullImage).attr("target","_blank");
                    $(esg.o.htmlControlFullImage).attr("href",url);
                } else {
                    $(esg.o.htmlControlFullImage).hide();
                }
            } else {
                $(esg.o.htmlControlFullImage).hide();
                $(esg.o.htmlControlFullImage).attr("target","_blank");
            }
            return true;
        };

        /**
		 * Playing slideshow.
		 */
		esg.slideshow = function() {
			esg.hideSummary();
			if (esg.isSlideshow) {
				esg.moveNext(true);
				setTimeout(function() {
					esg.slideshow();
				}, 3000);
			}
			if (esg.checkLast($(esg.o.htmlActive))) {
				esg.toggleSlideshow();
			}
		};



		/* ==================================================================================================================================
		 *  ... and rest
		 *  ================================================================================================================================== */

		/**
		 * Animate element for scrolling next/prev.
		 * @param {HTMLElement} el
		 * @param {String} dir
		 */
		esg.animateArrow = function(el, dir) {
			if (!esg.lockGlow) {
				esg.lockGlow = true;
				if ((dir == "in") || (dir == "both")) $(el + ' > span' + esg.o.htmlGlow).delay(100).fadeIn(400);
				if ((dir == "out") || (dir == "both")) $(el + ' > span' + esg.o.htmlGlow).delay(100).fadeOut(200);
				setTimeout(function() {
					esg.lockGlow = false;
				}, 300);
			}
		};

		/**
		 * @param {HTMLElement} e
		 */
		esg.keyCapture = function(e) {
			switch(e.keyCode) {
				case 39: esg.moveNext(true); break; // right
				case 38: esg.togglePlaylist(); break; // up
				case 32: esg.toggleSlideshow(); break; // spacebar
				case 37: esg.movePrev(true); break; // left
				case 40: esg.togglePlaylist(); break; // down
				case 36: esg.changeFromPlaylist($(esg.o.htmlMediaList + ' > ul > li:first-child > a')); break;  // home
				case 35: esg.changeFromPlaylist($(esg.o.htmlMediaList + ' > ul > li:last-child > a')); break; // end
			}
		};

		/**
		 * Set the numeric hash in URL.
		 * @param {HTMLElement} el
		 */
		esg.setHash = function(el) {
			var hash = Number(el.parent().attr("name"));
            var location = window.location.href;
			$(esg.o.htmlPrevLink).attr('href', '#' + (hash-1));
			$(esg.o.htmlNextLink).attr('href', '#' + (hash+1));
            if (esg.o.social) {
                $(esg.o.facebookLink).attr("href", esg.o.facebookSharer + esg.replaceHash(location) + '%23' + (hash));
                $(esg.o.twitterLink).attr("href", esg.o.twitterSharer + esg.replaceHash(location) + '%23' + (hash));
                $(esg.o.gplusLink).attr("href", esg.o.gplusSharer + esg.replaceHash(location) + '%23' + (hash));
                $(esg.o.htmlMediaLinkUrl).text(esg.replaceHash(location) + '#' + (hash));
            }
        };

		esg.setDefaultItem = function() {
			var defaultItemHash = '';
			if (window.location.hash) {
				defaultItemHash = window.location.hash;
			} else if (esg.hash) {
				defaultItemHash = esg.hash;
			}
			console.log(defaultItemHash);
			defaultItemHashLength = (defaultItemHash.length);
			defaultItemHashIndex = (defaultItemHash.lastIndexOf("#"));
			console.log(defaultItemHash);
			defaultItemHash = (defaultItemHash.substring(defaultItemHashIndex, defaultItemHashLength));
			console.log(defaultItemHash);
			defaultItemHash = (defaultItemHash.replace('#', '') - 1);
			console.log(defaultItemHash);
			if (defaultItemHash >= 0) {
				esg.hideSummary();
				return $(esg.o.htmlMediaList + ' > ul > li > a')[defaultItemHash];
			} else {
				return $(esg.o.htmlMediaList + ' > ul > li:first > a');
			}
		};

		esg.ie8Detection = function() {
			return ($.browser.msie) && (($.browser.version < '9.0'));
		};

		esg.getName = function(el) {
			if (el) {
                return el.replace('.', '').replace('#', '');
            } else {
                return false;
            }
		};

        esg.replaceHash = function(string) {
            return string.replace('#', '');
        };

        esg.openWindow = function(url, name) {
            window.open(url, name, 'width=' + esg.o.newWindowWidth + ',height=' + esg.o.newWindowHeight + ',left=' + esg.screenX + ',top=' + esg.screenY);
        }

		esg.init = function() {
			var html = esg.htmlWrapper();
			if (html) {

				esg.isIE8 = esg.ie8Detection();

				esg.initScrollbar(0);
				esg.changeWindowSize();
				esg.changeDefaultItem(esg.setDefaultItem());

				$(esg.o.htmlMediaList + ' > ul > li > a').click(function(e) {
					e.preventDefault();
					if (esg.isSlideshow) esg.toggleSlideshow();
					esg.changeFromPlaylist(this);
				});

				$(esg.o.htmlMediaSummary + ' > ul > li > a').click(function(e) {
					e.preventDefault();
					esg.changeFromSummary(this);
				});

				$(window).resize(function() {
					esg.changeWindowSize();
					esg.changeScrollbarPosition($(esg.o.htmlActive), $(esg.o.htmlActive));
				});

				if (!esg.isIE8) {
					window.addEventListener('orientationchange', function() {
						esg.changeWindowSize();
						esg.changeScrollbarPosition($(esg.o.htmlActive), $(esg.o.htmlActive));
					}, false);
				}

                $(esg.o.showLink)
                    .bind("click", function(e){
                        e.preventDefault();
                        $(esg.o.htmlMediaLink).show();
                    });

                if (esg.o.social) {
                    $(esg.o.htmlMediaContent).append('<script type="text/javascript" src="' + esg.o.zeroClipboardJs + '">' + '</' + 'script>');
                    var clip = new ZeroClipboard($(esg.o.htmlMediaLinkCopy), {
                        moviePath: esg.o.zeroClipboardSwf,
                        hoverClass: esg.o.htmlMediaLinkCopyHover
                    });
                    clip.on( 'complete', function(client, args) {
                        $(esg.o.htmlMediaLink).hide();
                    } );
                }

                $(esg.o.facebookLink)
                    .bind("click", function(e){
                        e.preventDefault();
                        esg.openWindow($(esg.o.facebookLink).attr('href'), "facebook");
                    });

                $(esg.o.twitterLink)
                    .bind("click", function(e){
                        e.preventDefault();
                        esg.openWindow($(esg.o.twitterLink).attr('href'), "twitter");
                    });

                $(esg.o.gplusLink)
                    .bind("click", function(e){
                        e.preventDefault();
                        window.open($(esg.o.gplusLink).attr('href'), "gplus", 'width=' + esg.o.newWindowWidth + ',height=' + esg.o.newWindowHeight + ',left=' + esg.screenX + ',top=' + esg.screenY);
                    });

				$(esg.o.htmlNextLink)
					.bind("click", function(e){
						e.preventDefault();
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.moveNext(false);
					})
					.bind("mouseenter", function() {
						esg.animateArrow(esg.o.htmlNextLink, 'in');
					})
					.bind("mouseleave", function() {
						esg.animateArrow(esg.o.htmlNextLink, 'out');
					});

				$(esg.o.htmlPrevLink)
					.bind("click", function(e) {
						e.preventDefault();
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.movePrev(false);
					})
					.bind("mouseenter", function() {
						esg.animateArrow(esg.o.htmlPrevLink, 'in');
					})
					.bind("mouseleave", function() {
						esg.animateArrow(esg.o.htmlPrevLink, 'out');
					});

				$(esg.o.htmlCloseLink).click(function(e) {
					if ($(esg.o.htmlCloseLink).attr("href") == "#") {
						e.preventDefault();
						esg.htmlDeWrapper();
					}
				});

				$('.' + esg.o.container).click(function(e) {
					e.stopPropagation();
				});

				$('.' + esg.o.containerOverlay).click(function(e) {
					e.preventDefault();
					esg.htmlDeWrapper();
				});

				$(esg.o.htmlControlCaption).click(function(e) {
					e.preventDefault();
					esg.toggleCaption();
				});

				$(esg.o.htmlControlPlaylist).click(function(e) {
					e.preventDefault();
					esg.togglePlaylist();
				});

				$(esg.o.htmlControlSlideshow).click(function(e) {
					e.preventDefault();
					esg.toggleSlideshow()
				});

				$(esg.o.htmlSummaryLink).click(function(e) {
					e.preventDefault();
					if (esg.isSlideshow) esg.toggleSlideshow();
					$(esg.o.htmlMediaContent).append('<span class="' + esg.getName(esg.o.htmlStopSlideshow) + '" />');
					setTimeout(function() {
						$(esg.o.htmlStopSlideshow).remove();
						esg.toggleSummary();
					}, 3000);
				});

				$(document).keydown(function(e) {
					esg.keyCapture(e);
				});

				$(esg.o.htmlMediaMainContainer).mousewheel(function(event, delta, deltaX, deltaY) {
					if (deltaY > 0) {
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.movePrev(true);
					} else if ((deltaY < 0)) {
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.moveNext(true);
					}
				});

				$(esg.o.htmlMediaMainContainer).on({
					'swipeleft' : function() {
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.moveNext(true);
					},
					'swiperight' : function() {
						if (esg.isSlideshow) esg.toggleSlideshow();
						esg.movePrev(true);
					}
				});
			}
		};

		return this.each(function() {

			if ($(esg.o.htmlMediaList + ' ul li').length == 0) {
				return false;
			}

            if (!esg.o.social) {
                $(esg.o.htmlMediaSocial).remove();
            }

			if (esg.o.onReady) {
				esg.init();
			} else {
				$(esg.o.htmlOpenLink).live('click', function(e) {
					e.preventDefault();
					if ($(this).attr('href')) esg.hash = $(this).attr('href').replace(/^.*#/, '');
					esg.init();
				});
			}
            return true;
		});

	};

}) ( jQuery );