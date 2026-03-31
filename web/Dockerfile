FROM node:22-alpine

WORKDIR /app

COPY web/package.json /app/package.json
RUN npm install

COPY web /app

RUN npm run build

CMD ["npm", "run", "start"]

