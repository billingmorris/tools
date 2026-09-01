/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillUnmount } from "@odoo/owl";

// ════════════════════════════════════════════════════════
//   CalculadoraPopup — lógica de la calculadora
// ════════════════════════════════════════════════════════
class CalculadoraPopup extends Component {
    static template = "calculadora_popup.CalculadoraPopup";

    setup() {
        this.state = useState({
            display: "0",
            expression: "",
            waitingOperand: false,
            operator: null,
            prevValue: null,
            history: [],
            hasError: false,
        });

        this._onKeyDown = this._onKeyDown.bind(this);
        document.addEventListener("keydown", this._onKeyDown);
        onWillUnmount(() => document.removeEventListener("keydown", this._onKeyDown));
    }

    // ── Dígitos y punto decimal ─────────────────
    onDigit(digit) {
        const s = this.state;
        if (s.hasError) { this._reset(); return; }
        if (digit === "." && s.display.includes(".")) return;

        if (s.waitingOperand) {
            s.display = digit === "." ? "0." : digit;
            s.waitingOperand = false;
        } else {
            s.display = s.display === "0" && digit !== "."
                ? digit
                : s.display + digit;
        }
    }

    // ── Operadores +  −  ×  ÷ ──────────────────
    onOperator(op) {
        const s = this.state;
        if (s.hasError) { this._reset(); return; }

        const current = parseFloat(s.display);

        if (s.operator && !s.waitingOperand) {
            const result = this._calc(s.prevValue, current, s.operator);
            if (result === null) { this._setError(); return; }
            s.display = this._fmt(result);
            s.prevValue = result;
        } else {
            s.prevValue = current;
        }

        s.operator = op;
        s.waitingOperand = true;
        s.expression = `${this._fmt(s.prevValue)} ${this._sym(op)}`;
    }

    // ── Acciones especiales ─────────────────────
    onAction(action) {
        const s = this.state;

        if (action === "clear") {
            this._reset();

        } else if (action === "backspace") {
            if (s.hasError || s.waitingOperand) return;
            s.display = s.display.length > 1 ? s.display.slice(0, -1) : "0";

        } else if (action === "sign") {
            if (s.hasError) return;
            const n = parseFloat(s.display) * -1;
            s.display = this._fmt(n);

        } else if (action === "percent") {
            if (s.hasError) return;
            s.display = this._fmt(parseFloat(s.display) / 100);

        } else if (action === "equals") {
            if (!s.operator || s.waitingOperand) return;
            const b = parseFloat(s.display);
            const result = this._calc(s.prevValue, b, s.operator);
            if (result === null) { this._setError(); return; }

            const expr = `${this._fmt(s.prevValue)} ${this._sym(s.operator)} ${this._fmt(b)} =`;
            s.history = [{ expr, result: this._fmt(result) }, ...s.history.slice(0, 9)];

            s.expression = expr;
            s.display = this._fmt(result);
            s.operator = null;
            s.prevValue = null;
            s.waitingOperand = true;

        } else if (action === "clearHistory") {
            s.history = [];
        }
    }

    onHistoryClick(item) {
        Object.assign(this.state, {
            display: item.result,
            expression: "",
            operator: null,
            prevValue: null,
            waitingOperand: false,
            hasError: false,
        });
    }

    onClose()        { this.props.onClose(); }
    onOverlayClick() { this.props.onClose(); }

    // ── Helpers ─────────────────────────────────
    _calc(a, b, op) {
        if (op === "+") return a + b;
        if (op === "-") return a - b;
        if (op === "*") return a * b;
        if (op === "/") return b === 0 ? null : a / b;
        return null;
    }

    _fmt(n) {
        if (n === null || isNaN(n) || !isFinite(n)) return "Error";
        const s = parseFloat(n.toPrecision(12)).toString();
        return s;
    }

    _sym(op) {
        return { "+": "+", "-": "−", "*": "×", "/": "÷" }[op] || op;
    }

    _reset() {
        Object.assign(this.state, {
            display: "0", expression: "",
            waitingOperand: false, operator: null,
            prevValue: null, hasError: false,
        });
    }

    _setError() {
        this.state.display = "Error";
        this.state.expression = "División por cero";
        this.state.hasError = true;
    }

    _onKeyDown(ev) {
        if (!document.querySelector(".o_calc_popup")) return;
        const k = ev.key;
        const map = {
            "0":"-","1":"-","2":"-","3":"-","4":"-",
            "5":"-","6":"-","7":"-","8":"-","9":"-",".":"-",
        };
        if ("0123456789.".includes(k))       { ev.preventDefault(); this.onDigit(k); }
        else if (k === "+")                  { ev.preventDefault(); this.onOperator("+"); }
        else if (k === "-")                  { ev.preventDefault(); this.onOperator("-"); }
        else if (k === "*")                  { ev.preventDefault(); this.onOperator("*"); }
        else if (k === "/")                  { ev.preventDefault(); this.onOperator("/"); }
        else if (k === "Enter" || k === "=") { ev.preventDefault(); this.onAction("equals"); }
        else if (k === "Backspace")          { ev.preventDefault(); this.onAction("backspace"); }
        else if (k === "Escape")             { ev.preventDefault(); this.onClose(); }
        else if (k === "Delete")             { ev.preventDefault(); this.onAction("clear"); }
    }
}

CalculadoraPopup.props = { onClose: Function };


// ════════════════════════════════════════════════════════
//   CalculadoraSystray — ícono en la barra superior
// ════════════════════════════════════════════════════════
class CalculadoraSystray extends Component {
    static template  = "calculadora_popup.SystrayButton";
    static components = { CalculadoraPopup };

    setup() {
        this.state = useState({ open: false });
    }

    get isOpen() { return this.state.open; }

    onClick()  { this.state.open = !this.state.open; }
    onClose()  { this.state.open = false; }
}


// ── Registro en el systray de Odoo ──────────
registry.category("systray").add("calculadora_popup.systray", {
    Component: CalculadoraSystray,
    sequence: 1,   // sequence bajo = aparece a la izquierda del grupo
});
