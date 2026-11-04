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
        enhanceBatchModelPicker();
    }

    // Keep the original select as the form/API source of truth; enhance only its presentation.
    function enhanceBatchModelPicker() {
        const select = document.querySelector('.research-batch select#model');
        if (!select) return;
        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'research-model-trigger';
        trigger.setAttribute('role', 'combobox');
        trigger.setAttribute('aria-haspopup', 'listbox');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.setAttribute('aria-controls', 'research-model-list');
        const label = document.createElement('span');
        const chevron = document.createElement('span');
        chevron.className = 'research-model-chevron';
        chevron.setAttribute('aria-hidden', 'true');
        trigger.append(label, chevron);
        const menu = document.createElement('div');
        menu.id = 'research-model-list';
        menu.className = 'research-model-menu';
        menu.setAttribute('role', 'listbox');
        menu.setAttribute('aria-hidden', 'true');
        menu.inert = true;
        select.after(trigger);
        document.body.append(menu);
        select.classList.add('research-native-select');
        select.tabIndex = -1;
        select.setAttribute('aria-hidden', 'true');
        let open = false, active = select.selectedIndex, search = '', searchTimer;
        const options = Array.from(select.options).map((option, index) => {
            const row = document.createElement('div');
            row.id = 'research-model-option-' + index;
            row.className = 'research-model-option';
            row.setAttribute('role', 'option');
            row.textContent = option.textContent;
            row.addEventListener('pointermove', () => highlight(index));
            row.addEventListener('click', () => choose(index));
            menu.append(row);
            return row;
        });
        function highlight(index) {
            active = index;
            options.forEach((row, i) => row.classList.toggle('is-highlighted', i === active));
            if (open && options[active]) trigger.setAttribute('aria-activedescendant', options[active].id);
        }
        function sync() {
            label.textContent = select.selectedOptions[0]?.textContent || '';
            trigger.disabled = select.disabled;
            trigger.setAttribute('aria-label', document.documentElement.lang === 'en' ? 'Choose an AI model' : '选择 AI 模型');
            options.forEach((row, i) => {
                row.textContent = select.options[i].textContent;
                row.setAttribute('aria-selected', String(i === select.selectedIndex));
                row.setAttribute('aria-disabled', String(select.options[i].disabled));
            });
            if (select.disabled) close();
        }
        function position() {
            const rect = trigger.getBoundingClientRect();
            if (rect.bottom < 0 || rect.top > window.innerHeight) { close(); return; }
            const height = Math.min(menu.scrollHeight, 240);
            const below = window.innerHeight - rect.bottom - 16;
            const above = rect.top - 16;
            const flip = below < height && above > below;
            const available = Math.max(48, flip ? above : below);
            menu.style.width = Math.min(rect.width, window.innerWidth - 24) + 'px';
            menu.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - rect.width - 12)) + 'px';
            menu.style.maxHeight = Math.min(240, available) + 'px';
            menu.style.top = (flip ? rect.top - Math.min(height, available) - 8 : rect.bottom + 8) + 'px';
            menu.classList.toggle('opens-up', flip);
        }
        function show() {
            if (select.disabled) return;
            sync();
            open = true;
            highlight(select.selectedIndex);
            position();
            menu.inert = false;
            menu.setAttribute('aria-hidden', 'false');
            menu.classList.add('is-open');
            trigger.setAttribute('aria-expanded', 'true');
        }
        function close() {
            open = false;
            menu.classList.remove('is-open');
            menu.inert = true;
            menu.setAttribute('aria-hidden', 'true');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.removeAttribute('aria-activedescendant');
        }
        function choose(index) {
            if (select.disabled || select.options[index].disabled) return;
            const changed = select.selectedIndex !== index;
            select.selectedIndex = index;
            sync();
            close();
            trigger.focus({preventScroll: true});
            if (changed) {
                select.dispatchEvent(new Event('input', {bubbles: true}));
                select.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }
        function move(direction) {
            for (let i = 1; i <= options.length; i++) {
                const next = (active + direction * i + options.length) % options.length;
                if (!select.options[next].disabled) { highlight(next); break; }
            }
        }
        trigger.addEventListener('click', () => open ? close() : show());
        trigger.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                if (!open) show(); else move(event.key === 'ArrowDown' ? 1 : -1);
            } else if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                if (open) choose(active); else show();
            } else if (event.key === 'Escape') {
                event.preventDefault(); close();
            } else if (event.key === 'Home' || event.key === 'End') {
                event.preventDefault();
                if (!open) show();
                const indices = Array.from(select.options, (_, i) => i).filter(i => !select.options[i].disabled);
                if (indices.length) highlight(event.key === 'Home' ? indices[0] : indices[indices.length - 1]);
            } else if (event.key === 'Tab') close();
            else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
                clearTimeout(searchTimer);
                search += event.key.toLowerCase();
                searchTimer = setTimeout(() => { search = ''; }, 600);
                if (!open) show();
                const index = Array.from(select.options).findIndex(o => !o.disabled && o.textContent.toLowerCase().startsWith(search));
                if (index >= 0) highlight(index);
            }
        });
        trigger.addEventListener('blur', close);
        menu.addEventListener('pointerdown', event => event.preventDefault());
        document.addEventListener('pointerdown', event => {
            if (open && !trigger.contains(event.target) && !menu.contains(event.target)) close();
        });
        window.addEventListener('resize', () => { if (open) position(); });
        document.addEventListener('scroll', event => { if (open && !menu.contains(event.target)) position(); }, true);
        select.addEventListener('change', sync);
        select.form?.addEventListener('reset', () => setTimeout(sync, 0));
        new MutationObserver(sync).observe(select, {attributes: true, attributeFilter: ['disabled'], subtree: true});
        new MutationObserver(sync).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
        sync();
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
