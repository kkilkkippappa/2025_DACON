const prefix = '[Hackathon]';

const formatMessage = (message) => `${prefix} ${message}`;

export const logger = {
  info(message, ...args) {
    console.info(formatMessage(message), ...args);
  },
  warn(message, ...args) {
    console.warn(formatMessage(message), ...args);
  },
  error(message, ...args) {
    console.error(formatMessage(message), ...args);
  },
  exception(message, error) {
    if (error instanceof Error) {
      console.error(formatMessage(`${message}: ${error.message}`), error);
    } else {
      console.error(formatMessage(message), error);
    }
  },
};
