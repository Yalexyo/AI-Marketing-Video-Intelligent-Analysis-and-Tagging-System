import { TypeORMError } from "./TypeORMError";
/** Thrown when transaction rollback fails */
export class TransactionRollbackFailedError extends TypeORMError {
    constructor(cause) {
        super("Transaction rollback failed", { cause });
    }
}

//# sourceMappingURL=TransactionRollbackFailedError.js.map
