export class TimeoutTimer {
    constructor(timeout) {
        this.timerPromise = new Promise((resolve) => {
            this.timeoutTimerId = setTimeout(resolve, timeout);
        });
    }
    get promise() {
        return this.timerPromise;
    }
    clear() {
        clearTimeout(this.timeoutTimerId);
    }
    static start(timeout) {
        return new TimeoutTimer(timeout);
    }
}

//# sourceMappingURL=Timer.js.map
