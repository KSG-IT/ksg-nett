// Some important elements
const canvasWrapperEl = document.getElementById('klinekart-wrapper')
const canvas = document.getElementById('klinekart-canvas')
const ctx = canvas.getContext('2d')
ctx.globalCompositeOperation = 'destination-in'

const thumbSize = 50

// Render flags and variables
let debug = false

// Camera constants
const cameraSpeed = 7
const cameraZoomSpeed = 1.1


// Get and set canvas size
const width = canvasWrapperEl.scrollWidth
const height = canvasWrapperEl.scrollHeight

canvas.width = width
canvas.height = height

const camera = {
  vx: 0,
  vy: 0,
  width: width,
  height: height,
  zoom: 1,
}

// Set up objects and variables required for interaction with the Mouse
const mouseInfo = {
  lastPosX: 0,
  lastPosY: 0,
  lastPosWorldSpaceX: 0,
  lastPosWorldSpaceY: 0,
  mouseDown: false,
  // This variable is used to check whether or not the mouse was just released. This is useful to detect clicks.
  mouseUpLastFrame: false,
  // This list contains tuples [id, distance], where id is the node id, and distance is the distance from the center of the node to the mouse
  intersectingUsersThisFrame: [],
  // Use to contain a reference the the currently dragged user
  userDragged: null
}

// Frame and update specific variables. The three first are used to implement a fixed timestep logic loop
let frameRate = 60
let logicUpdateTime = 1000/30 // ms
let lastUpdateFrame = 0
const logicUpdatesPerSecond = 30
const timeBetweenLogicUpdates = 1000 / logicUpdatesPerSecond
const maximumNumberOfLogicUpdatesMissingBeforeWeSkip = 3 * logicUpdatesPerSecond

let frameCount = 0
let lastFrameTimes = []
let lastLogicUpdateTimes = []
let framesSinceLastLogicSkip = Math.Infinity

// RANDOM USER GENERATION MODE
// Load and transform data
// const madeOutData = JSON.parse(
//   document.querySelector(
//     "meta[name='made-out-data']"
//   ).getAttribute('content')
// )
// 
// const users = {}
// const madeOutAssociationsSet = new Set()
// 
// const userCount = 1500
// const averageCons = 5
// 
// for (let i = 0; i < userCount; ++i){
//   users[i] = {id: i, name: "Epic kebab", img: "https://m.media-amazon.com/images/M/MV5BMjA5NTE4NTE5NV5BMl5BanBnXkFtZTcwMTcyOTY5Mw@@._V1_.jpg"}
// 
//   if (i + averageCons > userCount) {
//     continue
//   }
//   const madeOuts = Math.random() * averageCons
//   for (let j = 0; j < madeOuts; ++j) {
//     madeOutAssociationsSet.add([i, i + madeOuts * Math.random()].sort().join('|'))
//   }
// }
// 
// // const superMan = Math.random() * userCount
// // for (let i = 0; i < 20; ++i){
// //   madeOutAssociationsSet.add([superMan, Math.random() * userCount].sort().join("|"))
// // }
// 
// const madeOutAssociations = Array.from(madeOutAssociationsSet).map(assoc => assoc.split('|').map(x => parseInt(x)))
// const connectionCount = madeOutAssociations.length
// 
// const associationSiblingLookup = {}
// const associationSiblingArrayLookup =  {}
// const nodes = {}
// END RANDOM USER GENERATION MODE

// ========================== //
// INITIALIZATION             //
// ========================== //

// Load and transform data
const madeOutData = JSON.parse(
  document.querySelector(
    "meta[name='made-out-data']"
  ).getAttribute('content')
)

const users = {}

// Use this to make sure we only add each association once
const madeOutAssociationsSet = new Set()

madeOutData.forEach(association => {
  const firstUser = association[0]
  const secondUser = association[1]

  if (!(firstUser.id in users)){
    if (!firstUser.img) {
      firstUser.img = 'https://m.media-amazon.com/images/M/MV5BMjA5NTE4NTE5NV5BMl5BanBnXkFtZTcwMTcyOTY5Mw@@._V1_.jpg'
    }
    users[firstUser.id] = firstUser
  }

  if (!(secondUser.id in users)){
    if (!secondUser.img) {
      secondUser.img = 'https://m.media-amazon.com/images/M/MV5BMjA5NTE4NTE5NV5BMl5BanBnXkFtZTcwMTcyOTY5Mw@@._V1_.jpg'
    }
    users[secondUser.id] = secondUser
  }

  // The magic in the brackets simply make sure that the ids are sorted, and then
  // joined by a pipe:
  //    1, 2 => 1|2
  //    2, 1 => 1|2
  madeOutAssociationsSet.add([firstUser.id, secondUser.id].sort().join('|'))
})

const madeOutAssociations = Array.from(madeOutAssociationsSet).map(assoc => assoc.split('|').map(x => parseInt(x)))
const connectionCount = madeOutAssociations.length
const userCount = Object.keys(users).length

const associationSiblingLookup = {}
const associationSiblingArrayLookup = {}
const nodes = {}

// Set up node objects
Object.values(users).forEach(function (user) {
  nodes[user.id] = createNode(user, width * Math.random(), height * Math.random())
  associationSiblingLookup[user.id] = {}
  associationSiblingArrayLookup[user.id] = []
})

// Set up sibling lookups and association counts
madeOutAssociations.forEach(assoc => {
  const firstUserId = assoc[0]
  const secondUserId = assoc[1]

  const firstUserObject = {
    id: firstUserId,
    node: nodes[firstUserId],
    siblingNumber: nodes[secondUserId].assocCount
  }
  const secondUserObject = {
    id: secondUserId,
    node: nodes[secondUserId],
    siblingNumber: nodes[firstUserId].assocCount
  }

  associationSiblingLookup[firstUserId][secondUserId] = secondUserObject
  associationSiblingArrayLookup[firstUserId].push(secondUserObject)

  associationSiblingLookup[secondUserId][firstUserId] = firstUserObject
  associationSiblingArrayLookup[secondUserId].push(firstUserObject)

  nodes[firstUserId].assocCount += 1
  nodes[secondUserId].assocCount += 1
})

// When assocCounts are found we create the user canvases
Object.values(nodes).forEach(node => {
  createNodeCanvas(node)
})


// Create node islands
const nodeIslands = []
const inverseNodeIslandLookups = {}
let currentIsland = null
const nodesUsed = new Set()
const nodesRemaining = Array.from(Object.values(nodes).map(node => node.user.id))
const bfsList = []
let next = null

while(nodesRemaining.length > 0) {
  // This while loop is called once for every distinct island
  next = nodesRemaining.pop()
  if (nodesUsed.has(next)) {
    continue
  }

  currentIsland = createNodeIsland()
  // Add the next node to the bfsList
  bfsList.push(next)

  // Perform a DFS search over the graph.
  while(bfsList.length > 0) {
    const currentNode = nodes[next]

    if (nodesUsed.has(currentNode)) {
      continue
    }

    currentIsland.nodes.push(currentNode)
    currentIsland.mass += currentNode.assocCount
    inverseNodeIslandLookups[next] = currentIsland

    const siblings = associationSiblingLookup[next]
    Object.values(siblings).forEach(sibling => {
      if (nodesUsed.has(sibling.id)) {
        return
      }
      bfsList.push(sibling.id)
    })

    nodesUsed.add(next)
    next = bfsList.pop()
  }

  // Island is complete
  // We scale the mass by the sqrt
  currentIsland.mass = Math.sqrt(1 + currentIsland.mass)
  recalculateNodeIslandCentroid(currentIsland)
  nodeIslands.push(currentIsland)
}

const OPTIMIZE_NONE = 0
const OPTIMIZE_MILD = 1
const OPTIMIZE_MEDIUM = 2
const OPTIMIZE_AGGRESSIVE = 3

let optimizeSiblingStrategy = connectionCount > 2000 ? OPTIMIZE_AGGRESSIVE : connectionCount > 2500 ? OPTIMIZE_MEDIUM : connectionCount > 1000 ? OPTIMIZE_MILD : OPTIMIZE_NONE
let optimizeNodeStrategy = userCount > 10000 ? OPTIMIZE_AGGRESSIVE : userCount > 5000 ? OPTIMIZE_MEDIUM : userCount > 1000 ? OPTIMIZE_MILD : OPTIMIZE_NONE
let optimizeIslandStrategy = nodeIslands.length > 1000 ? OPTIMIZE_AGGRESSIVE : nodeIslands.length > 500 ? OPTIMIZE_MEDIUM : nodeIslands.length > 100 ? OPTIMIZE_MILD : OPTIMIZE_NONE
let optimizeRenderStrategy = userCount > 2000 ? OPTIMIZE_AGGRESSIVE : userCount > 1000 ? OPTIMIZE_MEDIUM : userCount > 500 ? OPTIMIZE_MILD : OPTIMIZE_NONE

// Physics constants
const nodesEquilibrium = 150
const springCoefficient = 0.005
const siblingRepulsionCoefficient = optimizeSiblingStrategy === OPTIMIZE_AGGRESSIVE ? 0.15 : 0.08
const islandRepulsionCoefficient = optimizeIslandStrategy === OPTIMIZE_AGGRESSIVE ? 50 : 5.5 
const springMaxSeparationLongerThanEquilibriumMax = -1000
const islandMaxSeparationThatYieldsForce = 10000
const islandMinSeparationForCalculation = 40
const damping = 0.1
const islandDamping = 0.005

function recalculateNodeIslandCentroid(island) {
  let sumXPos = 0
  let sumYPos = 0
  island.nodes.forEach(node => {
    sumXPos += node.x
    sumYPos += node.y
  })
  island.centroidX = sumXPos / island.nodes.length
  island.centroidY = sumYPos / island.nodes.length
}


function getCameraOffset () {
  return {
    x: camera.x - camera.width / 2,
    y: camera.y - camera.height / 2
  }
}

function createNodeIsland() {
  return {
    nodes: [],
    centroidX: 0,
    centroidY: 0,
    mass: 0,
    vx: 0,
    vy: 0,
    ax: 0,
    ay: 0
  }
}

function createNode (user, x, y) {
  const img = new Image()
  img.src = user.img

  return {
    id: user.id,
    user: user,
    x: x || 0,
    y: y || 0,
    vx: 0,
    vy: 0,
    ax: 0,
    ay: 0,
    img: img,
    imgLoaded: false,
    canvas: null,
    assocCount: 0
  }
}

function createNodeCanvas(node) {
  // Wait until the image is loaded
  node.img.onload = function(){
    node.imgLoaded = true
    const correlatedSize = thumbSize + 6 * node.assocCount

    const canvas = document.createElement("canvas")
    canvas.width = correlatedSize
    canvas.height = correlatedSize
    const ctx = canvas.getContext("2d")


    // Create a clip and render image into it
    ctx.beginPath();
    ctx.arc(correlatedSize/2, correlatedSize/2, correlatedSize/2, 0, Math.PI*2);
    ctx.clip()
    ctx.closePath();

    ctx.drawImage(node.img, 0, 0, correlatedSize, correlatedSize)

    node.canvas = canvas
  }
}

function update () {
  updateLogic()
  render()
  requestAnimationFrame(update)
}

function updateLogic () {
  const now = window.performance.now()

  if (now - lastUpdateFrame > timeBetweenLogicUpdates * maximumNumberOfLogicUpdatesMissingBeforeWeSkip) {
    framesSinceLastLogicSkip = 0
    lastUpdateFrame = now
  }

  // Catch up all necessary frames, we might be lagging behind multiple
  while(lastUpdateFrame < now) {

    updateAssociations()

    updateIslands()

    updateNodes()

    const updateTime = window.performance.now() - now

    // Add one frame time to the lastUpdateFrame variable
    lastLogicUpdateTimes.push(updateTime)

    if (updateTime > timeBetweenLogicUpdates) {
      const framesToSkip = Math.floor(updateTime / timeBetweenLogicUpdates)

      console.error("Logic update took too long, unable to keep up. Skipping " + framesToSkip + " frames.")
      lastUpdateFrame += framesToSkip * timeBetweenLogicUpdates
    }

    lastUpdateFrame += timeBetweenLogicUpdates
  }
}

function updateAssociations(){
  // Perform spring calculations
  madeOutAssociations.forEach(assoc => {
    const nodeOne = nodes[assoc[0]]
    const nodeTwo = nodes[assoc[1]]

    applySpringForce(nodeOne, nodeTwo)

    applySiblingForce(nodeOne, nodeTwo)
    applySiblingForce(nodeTwo, nodeOne)
  })

}

function updateNodes(){
  // Update velocity and positions
  Object.values(nodes).forEach(node => {
    // Abort if the node is currently being dragged, but reset acceleration. Also make sure to reset island velocity.
    if (mouseInfo.userDragged === node.user.id) {
      node.ax = 0
      node.ay = 0 

      const island = inverseNodeIslandLookups[node.user.id]
      island.vx = 0
      island.vy = 0

      return
    }

    node.vx += node.ax
    node.vy += node.ay

    // Apply island velocity
    const islandOfNode = inverseNodeIslandLookups[node.user.id]
    node.vx += islandOfNode.vx
    node.vy += islandOfNode.vy

    node.vx *= (1 - damping)
    node.vy *= (1 - damping)

    node.x += node.vx
    node.y += node.vy

    // Reset accelerations between each frame
    node.ax = 0
    node.ay = 0
  })
}

function updateIslands(){

  if (optimizeIslandStrategy === OPTIMIZE_AGGRESSIVE) {
    applyIslandForcesOptimizeAggressive()
  } else if (optimizeIslandStrategy > OPTIMIZE_MILD) {
    applyIslandForcesOptimizeMild()
  } else {
    applyIslandForcesNoOptimization()
  }

  // Update island velocities and centroids
  nodeIslands.forEach(island => {
    island.vx += island.ax
    island.vy += island.ay

    island.vx *= (1 - islandDamping)
    island.vy *= (1 - islandDamping)

    island.ax = 0
    island.ay = 0

    recalculateNodeIslandCentroid(island)
  })
}

function applyIslandForcesOptimizeAggressive(){
  for (let i = 0; i < nodeIslands.length; ++i) {
    const j = (i + 1) % nodeIslands.length

    const islandOne = nodeIslands[i]
    const islandTwo = nodeIslands[j]

    const distanceX = islandOne.centroidX - islandTwo.centroidX
    const distanceY = islandOne.centroidY - islandTwo.centroidY
    const distance = Math.max(islandMinSeparationForCalculation, Math.sqrt(distanceX * distanceX + distanceY * distanceY))
    const distanceCubed = distance * distance * distance

    if (distance > islandMaxSeparationThatYieldsForce) {
      continue
    }

    islandOne.ax += islandRepulsionCoefficient * islandTwo.mass * distanceX / distanceCubed
    islandOne.ay += islandRepulsionCoefficient * islandTwo.mass * distanceY / distanceCubed

    islandTwo.ax += -islandRepulsionCoefficient * islandOne.mass * distanceX / distanceCubed
    islandTwo.ay += -islandRepulsionCoefficient * islandOne.mass * distanceY / distanceCubed
  }
}

function applyIslandForcesOptimizeMild(){
  for (let i = 0; i < nodeIslands.length; ++i) {
    // Ignore every second island
    if (i % 2 === 0) {
      continue
    }
    const islandOne = nodeIslands[i]
    for (let j = i + 1; i !== j && j < nodeIslands.length; ++j) {
      // Ignore every second island
      if (j % 2 === 0) {
        continue
      }

      const islandTwo = nodeIslands[j]
      const distanceX = islandOne.centroidX - islandTwo.centroidX
      const distanceY = islandOne.centroidY - islandTwo.centroidY
      const distance = Math.max(islandMinSeparationForCalculation, Math.sqrt(distanceX * distanceX + distanceY * distanceY))
      const distanceCubed = distance * distance * distance

      if (distance > islandMaxSeparationThatYieldsForce) {
        continue
      }

      islandOne.ax += islandRepulsionCoefficient * islandTwo.mass * distanceX / distanceCubed
      islandOne.ay += islandRepulsionCoefficient * islandTwo.mass * distanceY / distanceCubed

      islandTwo.ax += -islandRepulsionCoefficient * islandOne.mass * distanceX / distanceCubed
      islandTwo.ay += -islandRepulsionCoefficient * islandOne.mass * distanceY / distanceCubed
    }
  }
}

function applyIslandForcesNoOptimization(){
  for (let i = 0; i < nodeIslands.length; ++i) {

    const islandOne = nodeIslands[i]
    for (let j = i + 1; i !== j && j < nodeIslands.length; ++j) {

      const islandTwo = nodeIslands[j]
      const distanceX = islandOne.centroidX - islandTwo.centroidX
      const distanceY = islandOne.centroidY - islandTwo.centroidY
      const distance = Math.max(islandMinSeparationForCalculation, Math.sqrt(distanceX * distanceX + distanceY * distanceY))
      const distanceCubed = distance * distance * distance

      if (distance > islandMaxSeparationThatYieldsForce) {
        continue
      }

      islandOne.ax += islandRepulsionCoefficient * islandTwo.mass * distanceX / distanceCubed
      islandOne.ay += islandRepulsionCoefficient * islandTwo.mass * distanceY / distanceCubed

      islandTwo.ax += -islandRepulsionCoefficient * islandOne.mass * distanceX / distanceCubed
      islandTwo.ay += -islandRepulsionCoefficient * islandOne.mass * distanceY / distanceCubed
    }
  }
}


function applySpringForce (nodeOne, nodeTwo) {
  const distanceX = nodeOne.x - nodeTwo.x
  const distanceY = nodeOne.y - nodeTwo.y

  const equilibriumCorrelator = Math.min(
    nodeOne.assocCount,
    nodeTwo.assocCount
  )

  let correlatedEquilibrium = nodesEquilibrium

  if (equilibriumCorrelator > 1) {
    correlatedEquilibrium *= (Math.pow(1.2, equilibriumCorrelator))
  }

  let distance = Math.sqrt(distanceX * distanceX + distanceY * distanceY)

  if (distance === 0) {
    distance = 0.1
  }

  const distanceFromIdeal = Math.max(correlatedEquilibrium - distance, springMaxSeparationLongerThanEquilibriumMax)
  const differenceVector = {
    x: distanceX / distance,
    y: distanceY / distance
  }

  nodeOne.ax += springCoefficient * distanceFromIdeal * differenceVector.x
  nodeOne.ay += springCoefficient * distanceFromIdeal * differenceVector.y

  nodeTwo.ax += -springCoefficient * distanceFromIdeal * differenceVector.x
  nodeTwo.ay += -springCoefficient * distanceFromIdeal * differenceVector.y
}

function applySiblingForce (node, parentNode) {
  if (optimizeSiblingStrategy === OPTIMIZE_AGGRESSIVE) {
    return applySiblingForceWithAggressiveOptimization(node, parentNode)
  }

  const siblingRelations = associationSiblingLookup[parentNode.user.id]

  const keys = Object.keys(siblingRelations)
  const indexOfNode = keys.indexOf(node.user.id)

  keys.forEach((siblingId, i) => {
    if (siblingId === node.user.id) {
      return
    }

    const sibling = siblingRelations[siblingId]
    // You are not your own sibling, this is not Alabama.

    const nodeSibling = nodes[sibling.id]

    const distanceX = nodeSibling.x - node.x
    const distanceY = nodeSibling.y - node.y

    // Make sure distance is not so small that the acceleration below blows up too much
    const distance = Math.max(0.001, Math.sqrt(distanceX * distanceX + distanceY * distanceY))

    node.ax -= siblingRepulsionCoefficient * distanceX / distance
    node.ay -= siblingRepulsionCoefficient * distanceY / distance
  })
}

function applySiblingForceWithAggressiveOptimization(node, parentNode) {
  const siblingRelations = associationSiblingLookup[parentNode.user.id]
  const nodeSiblingNumber = siblingRelations[node.user.id].siblingNumber
  const siblingThatShouldAffectUsId = (nodeSiblingNumber + 1) % parentNode.assocCount
  const siblingThatShouldAffectUs = associationSiblingArrayLookup[parentNode.user.id][siblingThatShouldAffectUsId]

  applyNodeConstantRepulsionForce(node, siblingThatShouldAffectUs.node, siblingRepulsionCoefficient)
}

function applyNodeConstantRepulsionForce(nodeOne, nodeTwo, coefficient) {
    const distanceX = nodeOne.x - nodeTwo.x
    const distanceY = nodeOne.y - nodeTwo.y

    // Make sure distance is not so small that the acceleration below blows up too much
    const distance = Math.max(0.001, Math.sqrt(distanceX * distanceX + distanceY * distanceY))

    nodeOne.ax += coefficient * distanceX / distance
    nodeOne.ay += coefficient * distanceY / distance

    nodeTwo.ax -= coefficient * distanceX / distance
    nodeTwo.ay -= coefficient * distanceY / distance
}

function render () {
  // Save the current zoom, which we persist between renders
  ctx.save();

  // Reset all transforms, so we can easily clear the entire canvas
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0, 0, width, height)

  // Draw static text while in identity-space
  ctx.font = '24px Arial '
  ctx.fillStyle = '#999'
  ctx.textAlign = "right"
  const titleText = "Klinekart  " + frameRate + "fps"
  ctx.fillText(titleText, width - 20, height - 20)

  // Static debug information
  if (debug) {
    ctx.textAlign = "left"
    ctx.fillText("1337 h4xx0r m0d3", 20, height - 20)

    ctx.fillText("Zoom: " + camera.zoom.toFixed(2), width - 350, height - 20)
    ctx.fillText("Node count: " + userCount.toFixed(0), width - 350, height - 42)
    ctx.fillText("Connection count: " + connectionCount.toFixed(0), width - 350, height - 64)
    ctx.fillText("Island count: " + nodeIslands.length, width - 350, height - 86)
    ctx.fillText("Average logic update time: " + logicUpdateTime, width - 350, height - 108)
  }

  // Restore the current zoom
  ctx.restore()

  // We still use our camera velocity variables to smoothly let key-inputs navigate the camera.
  ctx.translate(
    -cameraSpeed * camera.vx / camera.zoom,
    -cameraSpeed * camera.vy / camera.zoom,
  )

  // Render connections and nodes, in that order.
  renderConnections()

  // madeOutAssociations.forEach(assoc => renderConnection(assoc[0], assoc[1]))
  Object.keys(nodes).forEach(i => {
    renderNode(nodes[i])

    // Check intersection with mouse
    checkNodeIntersectionWithMouse(nodes[i])
  })

  // User is currently being dragged. Move the user
  if (mouseInfo.userDragged !== null && !mouseInfo.mouseUpLastFrame) {
    const node = nodes[mouseInfo.userDragged]

    node.x = mouseInfo.lastPosWorldSpaceX
    node.y = mouseInfo.lastPosWorldSpaceY
  } else {
    // Perform other mouse interaction checks

    // If there are intersecting users, take the nearest one, and render an outline and present user data
    const nearestUser = mouseInfo.intersectingUsersThisFrame.reduce(
      // Take "next" if and only if the distance is smaller than the previous smallest distance.
      // The distance is always the second value in the tuples
      (acc, next) => next[1] < acc[1] ? next : acc, 
      // The "default" user has no id and an infinite distance to the mouse
      [null, Infinity]
    )

    // A user is being hovered over
    if (nearestUser[0] !== null) {
      const node = nodes[nearestUser[0]]
      renderNodeBeingHoveredOver(node)
      document.body.style.cursor = "pointer"

      // Only perform the below actions if there is no currently dragged user

      if (mouseInfo.userDragged === null) {
        // User has been clicked
        if (mouseInfo.mouseUpLastFrame) {
          handleUserClicked(node.user)
        // User is now being dragged
        } else if (mouseInfo.mouseDown && mouseInfo.userDragged === null) {
          mouseInfo.userDragged = node.user.id
        }
      }
    } else {
      // Reset the mouse style in all non-hovering scenarios
      document.body.style.cursor = "default"
    }

    // If the mouse was up last frame, we always reset userDragged
    if (mouseInfo.mouseUpLastFrame){
      mouseInfo.userDragged = null
    }
  }

  // Capture current frame time. Update framerate every tenth frame
  if (lastFrameTimes.length > 50) {
    lastFrameTimes.shift()
  }
  lastFrameTimes.push(window.performance.now())
  ++frameCount;

  // Get new framerate. We do this unconditonallity when we're in debug mode.
  if (frameCount % 10 === 0 || debug) {
    frameRate = getCurrentFrameRate().toFixed(0)
  }

  if (lastLogicUpdateTimes.length > 50) {
    lastLogicUpdateTimes.shift()
  }
  logicUpdateTime = getCurrentLogicUpdateTime().toFixed(0)

  if (debug) {
    renderDebug()
  }

  // Reset pertinent values
  mouseInfo.intersectingUsersThisFrame = []
  mouseInfo.mouseUpLastFrame = false
}

function renderNode (node) {
  const correlatedSize = thumbSize + 6 * node.assocCount

  const xPos = node.x - correlatedSize / 2 
  const yPos = node.y - correlatedSize / 2

  if (!node.imgLoaded){
    // Draw a gray circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, correlatedSize/2, 0, 2*Math.PI);
    ctx.fillStyle = '#aaa';
    ctx.fill();
    return
  }

  // Draw canvas if the zoom is not too close. For close zooms we draw the full image
  if (camera.zoom < 0.85){
    ctx.drawImage(node.canvas, xPos, yPos)
  } else {
    ctx.save()
    // Create a clip and render image into it
    // ctx.save()
    ctx.beginPath();
    ctx.arc(node.x, node.y, correlatedSize/2, 0, Math.PI*2);
    ctx.clip()
    ctx.closePath();

    ctx.drawImage(node.img, xPos, yPos, correlatedSize, correlatedSize)
    ctx.restore()
  }
}

// Render all connections. We do this in a single path call
function renderConnections(lineWidth=1, strokeStyle="black") {
  ctx.save()
  ctx.beginPath()
  ctx.lineWidth = lineWidth
  ctx.strokeStyle = strokeStyle
  madeOutAssociations.forEach(assoc => {
    const firstNode = nodes[assoc[0]]
    const secondNode = nodes[assoc[1]]

    ctx.moveTo(firstNode.x, firstNode.y)
    ctx.lineTo(secondNode.x, secondNode.y)
  })
  ctx.stroke()
  ctx.restore()
}

function renderConnection(i, j, lineWidth=1, strokeStyle="black") {
  const firstNode = nodes[i]
  const secondNode = nodes[j]

  ctx.save()
  ctx.beginPath()
  ctx.lineWidth = lineWidth
  ctx.strokeStyle = strokeStyle
  ctx.moveTo(firstNode.x, firstNode.y)
  ctx.lineTo(secondNode.x, secondNode.y)
  ctx.stroke()
  ctx.restore()
}

function renderNodeUserText(node, size=18, color="black") {
  const correlatedSize = thumbSize + 6 * node.assocCount

  const xPos = node.x
  const yPos = node.y

  ctx.save()
  ctx.font = size + 'px Arial'
  ctx.textAlign="center"; 
  ctx.fillStyle = color
  ctx.fillText(node.user.name, xPos, yPos - correlatedSize/2 - 15)
  ctx.restore()
}

function renderNodeBeingHoveredOver(node) {
  const correlatedSize = thumbSize + 6 * node.assocCount

  const xPos = node.x
  const yPos = node.y

  // Draw thicker lines to neighbors, and draw text 
  const siblings = associationSiblingLookup[node.user.id]
  Object.values(siblings).forEach(sibling => {
    // Highlight connection
    renderConnection(node.user.id, sibling.id, 3, "#D83480")

    // Rerender node text
    renderNodeUserText(sibling.node, 18, '#D83480')

    // Rerender nodes to get them on top of connections
    renderNode(sibling.node)
  })

  // Render a blurred outline
  ctx.save()
  const radialGradient = ctx.createRadialGradient(xPos, yPos, 0, xPos, yPos, correlatedSize/1.5);
  radialGradient.addColorStop(0, 'rgba(216, 52, 128, 1)');
  radialGradient.addColorStop(0.8, 'rgba(216, 52, 128, 0.9)');
  radialGradient.addColorStop(1, 'rgba(216, 52, 128, 0)');

  ctx.fillStyle = radialGradient;
  ctx.fillRect(xPos - correlatedSize, yPos - correlatedSize, correlatedSize * 2.5, correlatedSize * 2.5);
  ctx.restore()

  // Rerender node, to get it in top of connections and outline
  renderNode(node)

  // Render title text
  renderNodeUserText(node, 26, '#D90368')
}

function renderDebug() {
  ctx.save()
  ctx.font = '18px Arial'
  ctx.textAlign="center"; 

  nodeIslands.forEach((island, i) => {
    ctx.fillText("Island " + (i + 1).toString(), island.centroidX, island.centroidY - 22)
    ctx.fillText("Centroid: (" + island.centroidX.toFixed(2) + ", " + island.centroidY.toFixed(2) +")", island.centroidX, island.centroidY)
    ctx.fillText("Velocity: (" + island.vx.toFixed(2) + ", " + island.vy.toFixed(2) +")", island.centroidX, island.centroidY + 22)
    ctx.fillText("Mass: " + island.mass.toFixed(2), island.centroidX, island.centroidY + 44)
  })
  ctx.restore()
}

function checkNodeIntersectionWithMouse(node) {
  const correlatedSize = (thumbSize + 6 * node.assocCount) / 2
  const xPos = node.x
  const yPos = node.y

  const diffX = mouseInfo.lastPosWorldSpaceX - xPos
  const diffY = mouseInfo.lastPosWorldSpaceY - yPos

  const distanceSquaredToCamera = diffX * diffX + diffY * diffY

  if (distanceSquaredToCamera < correlatedSize * correlatedSize) {
    mouseInfo.intersectingUsersThisFrame.push([node.user.id, distanceSquaredToCamera])
  }
}

function handleKeydown (event) {
  switch (event.key) {
    case 'ArrowUp':
    case 'w':
      camera.vy = -1
      break
    case 'ArrowLeft':
    case 'a':
      camera.vx = -1
      break
    case 'ArrowRight':
    case 'd':
      camera.vx = 1
      break
    case 'ArrowDown':
    case 's':
      camera.vy = 1
      break
  }
}

function handleKeyup (event) {
  switch (event.key) {
    case 'ArrowUp':
    case 'w':
      camera.vy = 0
      break
    case 'ArrowLeft':
    case 'a':
      camera.vx = 0
      break
    case 'ArrowRight':
    case 'd':
      camera.vx = 0
      break
    case 'ArrowDown':
    case 's':
      camera.vy = 0
      break
    case 'p':
      debug = !debug
      break
    case 'o':
      resetCamera()
      break
    case 'r':
      randomizePositions()
      break
  }
}

function handleScroll (event) {
  // Either wheelDelta or detail contains our desired zoom factor. They are differently scaled, hence the division.
  const delta = event.wheelDelta ? event.wheelDelta / 40 : event.detail ? -event.detail : 0
  if (delta) {
    const zoom = Math.pow(cameraZoomSpeed, delta)
    camera.zoom *= zoom

    const currentMousePos = getMousePos(event)
    // Get position in world-space
    const transformedMousePos = transformPointFromScreenSpaceToWorldSpace(currentMousePos.x, currentMousePos.y)

    // Zoom on mouse 
    ctx.translate(transformedMousePos.x, transformedMousePos.y)
    ctx.scale(zoom, zoom)
    ctx.translate(-transformedMousePos.x, -transformedMousePos.y)
  }
  return event.preventDefault() && false
}

function handleMouseDown(event) {
  mouseInfo.mouseDown = true
}

function handleMouseUp(event) {
  mouseInfo.mouseDown = false
  mouseInfo.mouseUpLastFrame = true
}

function handleMouseMove(event) {
  const currentMousePos = getMousePos(event)

  // Get position in world-space
  const transformedMousePos = transformPointFromScreenSpaceToWorldSpace(currentMousePos.x, currentMousePos.y)

  // Get last mouse position in current world-space
  // We cannot simply calculate differences in world-space coordinates, 
  // as they should be almost stationary when we move the mouse; thats the whole idea.
  const lastPosNowWorldSpace = transformPointFromScreenSpaceToWorldSpace(mouseInfo.lastPosX, mouseInfo.lastPosY)
  
  const deltaPos = {
    x: transformedMousePos.x - lastPosNowWorldSpace.x,
    y: transformedMousePos.y - lastPosNowWorldSpace.y,
  }

  // Update "last" values
  mouseInfo.lastPosX = currentMousePos.x
  mouseInfo.lastPosY = currentMousePos.y

  mouseInfo.lastPosWorldSpaceX = transformedMousePos.x
  mouseInfo.lastPosWorldSpaceY = transformedMousePos.y

  // Abort the translation if the mouse is not down, or if user is being dragged
  if (!mouseInfo.mouseDown || mouseInfo.userDragged !== null) {
    return
  }

  ctx.translate(
    deltaPos.x,
    deltaPos.y,
  )
}

function getMousePos(event) {
  var rect = canvas.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}

function transformPointFromScreenSpaceToWorldSpace(x, y){
  // Transforming the position from screen space to world-space is done consicely here by getting the current ctx matrix.
  // The current transform represents world-space to screen-space, and hence we want the inverse. Note that this matrix is by definition not singular.
  const currentTransformMatrix = ctx.getTransform()
  const inverseTransformMatrix = currentTransformMatrix.invertSelf()

  return  {
    // Standard matrix multiplication. Note that the matrix is really a 4x4 transformation matrix,
    // and with the fourth column contains the translation offsets.
    x: x * inverseTransformMatrix.m11 + y * inverseTransformMatrix.m12 + inverseTransformMatrix.m41,
    y: x * inverseTransformMatrix.m21 + y * inverseTransformMatrix.m22 + inverseTransformMatrix.m42,
  }
}

function randomizePositions(){
  Object.values(nodes).forEach(node => {
    node.x = Math.random() * width
    node.y = Math.random() * height
  })
}

function resetCamera(){
  ctx.setTransform(1, 0, 0, 1, 0, 0)
}

function getCurrentFrameRate(){
  if (lastFrameTimes.length === 0) {
    return 60  // We assume that we are awesome
  }
  // Differences between the last frames
  let deltas = []
  for (let i = 1; i < lastFrameTimes.length; ++i)  {
    deltas.push(lastFrameTimes[i] - lastFrameTimes[i-1])
  }

  // Calculate median
  const halfLength = Math.floor(deltas.length / 2)
  deltas = deltas.sort()
  let frameLength = 16
  if (deltas.length % 2 === 0) {
    frameLength =  0.5 * (deltas[halfLength] + deltas[halfLength - 1])
  } else {
    frameLength =  deltas[halfLength]
  }
  return 1000.0 / frameLength
}

function getCurrentLogicUpdateTime(){
  if (lastLogicUpdateTimes.length === 0) {
    return 1000 / logicUpdatesPerSecond  // We assume that we are awesome
  }

  // Calculate median
  const halfLength = Math.floor(lastLogicUpdateTimes.length / 2)
  sorted = Array.from(lastLogicUpdateTimes).sort()

  if (sorted.length % 2 === 0) {
    return 0.5 * (sorted[halfLength] + sorted[halfLength - 1])
  } else {
    return sorted[halfLength]
  }
}


function handleUserClicked(user) {
  if (user.id >= 0){
    // Go to user page
    window.location.href = '/internal/users/' + user.id
  }
}

requestAnimationFrame(update)

document.addEventListener('keydown', handleKeydown)
document.addEventListener('keyup', handleKeyup)

canvas.addEventListener('DOMMouseScroll', handleScroll, false)

canvas.addEventListener('mousewheel', handleScroll, false)
canvas.addEventListener('mousedown', handleMouseDown)
canvas.addEventListener('mousemove', handleMouseMove)
canvas.addEventListener('mouseup', handleMouseUp)
