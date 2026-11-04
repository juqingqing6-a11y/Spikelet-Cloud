/* Presentation only. Analysis, authentication and task handling remain in the original scripts. */
(() => {
    'use strict';
    function syncPresentationLanguage() {
        const language = localStorage.getItem('language') === 'en' ? 'en' : 'cn';
        document.documentElement.lang = language === 'en' ? 'en' : 'zh-CN';
        document.querySelectorAll('[data-ui-cn][data-ui-en]').forEach(element => {
            element.textContent = element.dataset[language === 'en' ? 'uiEn' : 'uiCn'].replace(/\\n/g, '\n');
        });
        document.querySelectorAll('#chinese, #english').forEach(element => {
            element.setAttribute('aria-current', (element.id === 'english') === (language === 'en') ? 'true' : 'false');
        });
    }
    function ready() {
        syncPresentationLanguage();
        window.addEventListener('load', syncPresentationLanguage, {once: true});
        document.querySelectorAll('#chinese, #english').forEach(element => {
            element.addEventListener('click', () => setTimeout(syncPresentationLanguage, 0));
        });
        installTactileFeedback();
    }

    // Observe native input events. Never intercept a click, submit, upload or navigation.
    function installTactileFeedback() {
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        const selector = 'button, .btn, [role="button"], #directory-input-label, .left-box .item, #chinese, #english';
        const pressed = new Map();
        const animations = new WeakMap();
        function control(target) {
            if (!(target instanceof Element)) return null;
            const element = target.closest(selector);
            return element && !element.matches(':disabled, [aria-disabled="true"]') ? element : null;
        }
        function press(element, key) {
            if (!element || reducedMotion.matches || pressed.has(key)) return;
            animations.get(element)?.cancel();
            element.classList.add('is-pressing');
            pressed.set(key, element);
        }
        function release(key, rebound = true) {
            const element = pressed.get(key);
            if (!element) return;
            pressed.delete(key);
            element.classList.remove('is-pressing');
            if (!rebound || reducedMotion.matches || element.matches(':disabled') || !element.animate) return;
            const animation = element.animate([
                {transform: 'scale(.965)'},
                {transform: 'scale(1.025)', offset: .5},
                {transform: 'scale(.995)', offset: .78},
                {transform: 'scale(1)'}
            ], {duration: 420, easing: 'cubic-bezier(.2,.7,.25,1)'});
            animations.set(element, animation);
            animation.finished.then(() => {
                if (animations.get(element) === animation) animations.delete(element);
            }).catch(() => {}); // A second press deliberately cancels the previous release.
        }
        function clear() { for (const key of pressed.keys()) release(key, false); }
        document.addEventListener('pointerdown', event => {
            if (event.button === 0) press(control(event.target), event.pointerId);
        }, {passive: true});
        document.addEventListener('pointerup', event => release(event.pointerId), {capture: true, passive: true});
        document.addEventListener('pointercancel', event => release(event.pointerId, false), {passive: true});
        document.addEventListener('pointerout', event => {
            const element = pressed.get(event.pointerId);
            if (element && !element.contains(event.relatedTarget)) release(event.pointerId, false);
        }, {passive: true});
        document.addEventListener('keydown', event => {
            if (!event.repeat && (event.key === 'Enter' || event.key === ' ')) press(control(event.target), event.key);
        });
        document.addEventListener('keyup', event => release(event.key), true);
        window.addEventListener('blur', clear);
        document.addEventListener('visibilitychange', () => { if (document.hidden) clear(); });
        reducedMotion.addEventListener('change', () => {
            clear();
            if (reducedMotion.matches) document.querySelectorAll(selector).forEach(element => animations.get(element)?.cancel());
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
    else ready();
})();
