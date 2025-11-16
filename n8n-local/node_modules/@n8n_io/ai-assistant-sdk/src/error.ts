export type Level = 'warning' | 'error' | 'fatal' | 'info';

export type ReportingOptions = {
	level?: Level;
	name?: string;
};

export class ApplicationError extends Error {
	level: Level;
	name: string;

	constructor(message: string, { level, name }: Partial<ErrorOptions> & ReportingOptions = {}) {
		super(message);
		this.level = level ?? 'error';
		this.name = name ?? 'AIServiceSDKError';
	}
}

export class APIResponseError extends ApplicationError {
	constructor(message: string) {
		super(message, { name: 'AIServiceAPIResponseError', level: 'error' });
	}
}

export class AuthError extends ApplicationError {
	constructor(message: string) {
		super(message, { name: 'AuthError', level: 'warning' });
	}
}
