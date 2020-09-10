/* global twemoji */
const MESSAGE_TYPE_MESSAGE_ADDED = 'message'
const MESSAGE_TYPE_USER_JOINED = 'user-joined'
const MESSAGE_TYPE_USER_LEFT = 'user-left'
const MESSAGE_TYPE_INITIALIZE = 'initialize'

// Cache the current user id. This is used to 
// figure out which messages are yours and not.
const currentUserId = parseInt(document
  .querySelector("meta[name=current-user-id]")
  .getAttribute("content")
)

// We store all current online users in this map
let users = new Map()

// We store all messages in this map
let messages = new Array()


// ============================= //
//  INITIALIZATION               //
// ============================= //
// Some relevant elements
const roomList = document.querySelector(".chat__roomlist")
const chatContents = document.querySelector(".chat__contents")
const inputEl = document.querySelector(".chat__input")
const sendEl = document.querySelector(".chat__inputsend")


const chatSocket = new WebSocket(
  (window.location.protocol === "https:" ? "wss" : "ws") + "://" + 
  window.location.host + 
  "/ws/chat/"
)
  
chatSocket.onmessage = handleWebsocketMessage
chatSocket.onclose = handleWebsocketClosed
chatSocket.onerror = console.log
  
  
// ============================= //
// SERVER HANDLING FUNCTIONALITY //
// ============================= //

/**
 * This is the root method handling incoming web socket data.
 * 
 * All incoming data is on the format:
 *    {
 *      "type": String,
 *       ...
 *    }
 * where the ellipses represent arbitrary key-value pairs. The type describes what type
 * of message is being received.
 * 
 * This methods primary responsibility is passing along data.
 * 
 * @param {Event} event The incoming websocket event.
 */
function handleWebsocketMessage(event) {
  // All received data is JSON
  const data = JSON.parse(event.data)

  switch(data.type) {
    case MESSAGE_TYPE_MESSAGE_ADDED:
      handleMessageAdded(data['message'], data['user'], data['timestamp'])
      break
    case MESSAGE_TYPE_USER_JOINED:
      handleUserJoinedChat(data['user'])
      break
    case MESSAGE_TYPE_USER_LEFT:
      handleUserLeftChat(data['user'])
      break
    case MESSAGE_TYPE_INITIALIZE:
      handleInitialize(data['users'], data['messages'])
      break
    default:
      console.log(data)
  }
  
}

/**
 * Handler called if the web socket connection fails.
 * @param {Event} event The error event
 */
function handleWebsocketClosed(event) {
  console.error("Fatal error", event)
}

/**
 * Handler for when a new message was sent to the chat, from some user.
 * 
 * @param {String} message The new message contents
 * @param {Object} user The user sending the message
 * @param {String} timestamp A timestamp for when the message was sent.
 */
function handleMessageAdded(message, user, timestamp) {
  addMessage(message, user, timestamp)
  renderMessage(message, user, timestamp)  
}

/**
 * Handler for when a new user joins the chat.
 * 
 * @param {Object} user The user that just joined
 */
function handleUserJoinedChat(user) {
  addUser(user)
  renderUserList()
}

/**
 * Handler for when a user leaves the chat.
 * 
 * @param {Object} user The id of the user that just left
 */
function handleUserLeftChat(user) {
  removeUser(user)
  renderUserList()
}

/**
 * Handler for when an initialization message has been received.
 * 
 * The initialization message typically contain the current online users, and the
 * last (50 or so) messages sent to the chat.
 * 
 * @param {Array} users All current users
 * @param {Array} messages The last (50 or so) messages that have been sent in the chat.
 */
function handleInitialize(users, messages){
  addUsers(users)
  addMessages(messages)

  messages.forEach(message => {
    renderMessage(message.message, message.user, message.timestamp)  
  })
  renderUserList()
  // Always move to bottom after initialization
  chatContents.scrollTop = chatContents.scrollHeight;
}

// ============================= //
//  STATE HANDLING               //
// ============================= //

/**
 * Add a message to our state.
 * 
 * @param {String} message The new message contents
 * @param {Object} user The user sending the message
 * @param {String} timestamp A timestamp for when the message was sent.
 */
function addMessage(message, user, timestamp){
  messages = messages.concat(message)
}

/**
 * Add a number of new messages to our state.
 * 
 * @param {Array} messages A number of new messages
 */
function addMessages(messages){
  messages.forEach(message => addMessage(message.message, message.user, message.timestamp))
}

/**
 * 
 * @param {Array} users A number of new users
 */
function addUsers(users) {
  users.forEach(user => addUser(user))
}

/**
 * Add a new user.
 * 
 * @param {Object} user The new user
 */
function addUser(user) {
  users.set(user.id, user)
}


/**
 * Remove a user.
 * 
 * @param {String} user The id of the user to be removed
 */
function removeUser(user) {
  users.delete(user)
}

// ====================================== //
//  RENDER AND DOM MANIPULATION FUNCTIONS //
// ====================================== //

/**
 * This template renders a thumbnail.
 * 
 * @param {String} url The image url of the thumbnail
 * @param {String} size The size of the thumbnail. Accepted sizes are tiny, smaller, smaller, medium, large, huge.
 * @param {String} title Any title to render on hover of the thumbnail.
 */
const thumbnailTemplate = (url, size="tiny", title="") => `
  <span class="thumb__${size}" title="${title}">
    <span class="thumb__inner" style="background-image: url('${url || 'https://m.media-amazon.com/images/M/MV5BMjA5NTE4NTE5NV5BMl5BanBnXkFtZTcwMTcyOTY5Mw@@._V1_UY317_CR20,0,214,317_AL_.jpg'}')">
    </span>
  </span>
`

/**
 * This template renders a new chat entry, either yours or someone elses.
 * 
 * @param {String} message The new message contents
 * @param {Object} user The user sending the message
 * @param {String} timestamp A timestamp for when the message was sent.
 */
const chatEntryTemplate = (message, user, timestamp) => `
  <div class="chat__entry${user.id === currentUserId ? ' chat__entry--you': ''}">
    <div class="chat__entrytext" title="${timestamp}">${message}</div>
    <div class="chat__entrythumb">
      ${thumbnailTemplate(user.img, "tiny", user.name)}
    </div>
  </div>
`

/**
 * Renders a new entry in the person overview list.
 * 
 * @param {Object} user The user
 */
const chatPersonOverviewTemplate = (user) => `
  <a href="/internal/users/${user.id}" class="resetlink" target="_blank">
    <li class="chat__personoverview">
      ${thumbnailTemplate(user.img)}
      <span class="chat__persontext">
        ${user.name}
      </span>
    </li>
  </a>
`

/**
 * Rerender the users into the roomList, aka the person overview.
 * 
 * The users are stored in the "users" Map. We use a map to get unique entries.
 * 
 * 
 */
function renderUserList() {
  const userObjects = Array.from(users.values())

  let userObjectsSorted = userObjects.sort((x, y) => {
    if (x.name > y.name) {
      return 1
    } else if (x.name < y.name) {
      return -1
    } else {
      return 0
    }
  })

  roomList.innerHTML = userObjectsSorted.reduce((acc, user) => acc + "\n" + chatPersonOverviewTemplate(user), "")
}

function renderMessage(message, user, timestamp) {
  const currentlyAtBottom = Math.abs(chatContents.scrollHeight - chatContents.scrollTop - chatContents.clientHeight) < 100;
  const emojiParsedMessage = twemoji.parse(message)
  chatContents.innerHTML += chatEntryTemplate(emojiParsedMessage, user, timestamp)

  if (currentlyAtBottom || user.id !== currentUserId) {
    // Wait until the next frame to jump down
    requestAnimationFrame(() => {
        // Go to end
        chatContents.scrollTop = chatContents.scrollHeight;
    })
  }
}

// ============================= //
//  INPUT HANDLING               //
// ============================= //

function sendMessage(message) {
  if (message === "") {
    return
  }
  chatSocket.send(JSON.stringify({
    message: message
  }))
  inputEl.value = ""
}

function handleInput(event){
  if (event.key === "Enter" && !event.shiftKey) {
    sendMessage(event.target.value)
    event.preventDefault()
  }
}

function handleSendButtonClicked(event){
  sendMessage(inputEl.value)  
  event.preventDefault()
}

// ============================= //
//  SET UP EVENT LISTENERS       //
// ============================= //
inputEl.addEventListener('keydown', handleInput) 
sendEl.addEventListener('mouseup', handleSendButtonClicked)

