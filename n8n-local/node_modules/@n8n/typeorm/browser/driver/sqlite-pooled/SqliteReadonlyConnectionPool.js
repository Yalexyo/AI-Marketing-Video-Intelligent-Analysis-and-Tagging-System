import assert from "node:assert";
import { Pool } from "tarn";
import { DriverAlreadyReleasedError } from "../../error/DriverAlreadyReleasedError";
import { LeasedDbConnection } from "./LeasedDbConnection";
const SQLITE_OPEN_READONLY = 1;
/**
 * Pool of read-only connections to the database.
 */
export class SqliteReadonlyConnectionPool {
    constructor(sqlite, options) {
        this.sqlite = sqlite;
        this.options = options;
        /**
         * Connections that are marked as invalid and should be destroyed
         */
        this.invalidConnections = new WeakSet();
        /** Currently leased connections */
        this.dbLeases = new Set();
        /** Has the pool been released */
        this.isReleased = false;
        assert(this.options.poolSize > 0);
        this.pool = this.createReadonlyPool();
    }
    async connect() {
        // Do nothing, connections are acquired on demand
    }
    async close() {
        for (const dbLease of this.dbLeases) {
            dbLease.requestRelease();
        }
        await this.pool.destroy();
    }
    async runExclusive(dbLeaseHolder, callback) {
        if (this.isReleased) {
            throw new DriverAlreadyReleasedError();
        }
        const dbConnection = await this.pool.acquire().promise;
        const dbLease = new LeasedDbConnection(dbConnection, this, dbLeaseHolder);
        this.dbLeases.add(dbLease);
        try {
            return await callback(dbLease);
        }
        finally {
            this.releaseConnection(dbLease);
        }
    }
    async leaseConnection(dbLeaseHolder) {
        if (this.isReleased) {
            throw new DriverAlreadyReleasedError();
        }
        const dbConnection = await this.pool.acquire().promise;
        return new LeasedDbConnection(dbConnection, this, dbLeaseHolder);
    }
    releaseConnection(leasedDbConnection) {
        if (leasedDbConnection.isInvalid) {
            this.invalidConnections.add(leasedDbConnection.connection);
        }
        this.dbLeases.delete(leasedDbConnection);
        this.pool.release(leasedDbConnection.connection);
    }
    validateDatabaseConnection(dbConnection) {
        return !this.invalidConnections.has(dbConnection);
    }
    createReadonlyPool() {
        const pool = new Pool({
            acquireTimeoutMillis: this.options.acquireTimeout,
            destroyTimeoutMillis: this.options.destroyTimeout,
            create: async () => {
                return await this.sqlite.createDatabaseConnection(SQLITE_OPEN_READONLY);
            },
            validate: (dbConnection) => {
                return this.validateDatabaseConnection(dbConnection);
            },
            destroy: async (dbConnection) => {
                this.invalidConnections.delete(dbConnection);
                return await this.sqlite.destroyDatabaseConnection(dbConnection);
            },
            min: 1,
            max: this.options.poolSize,
        });
        return pool;
    }
}

//# sourceMappingURL=SqliteReadonlyConnectionPool.js.map
