import { TypeORMError } from "./TypeORMError";
/** Thrown when an invariant is violated */
export class InvariantViolatedError extends TypeORMError {
    constructor(message = "Invariant violated", options = {}) {
        super(message, options);
    }
}

//# sourceMappingURL=InvariantViolatedError.js.map
