import { TypeORMError } from "./TypeORMError";
/** Thrown when transaction commit fails */
export class TransactionCommitFailedError extends TypeORMError {
    constructor(cause) {
        super("Transaction commit failed", { cause });
    }
}

//# sourceMappingURL=TransactionCommitFailedError.js.map
