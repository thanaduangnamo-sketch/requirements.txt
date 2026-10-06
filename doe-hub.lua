-- Services
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")
local LocalPlayer = Players.LocalPlayer
local PlayerGui = LocalPlayer:WaitForChild("PlayerGui")

-- ลบ GUI เก่าทิ้งก่อนป้องกันการซ้ำซ้อน
if PlayerGui:FindFirstChild("DOEHubPaidGui") then
	PlayerGui.DOEHubPaidGui:Destroy()
end

-- ตั้งค่ารหัส Key ที่ต้องการ
local CORRECT_KEY = "KEY-77FF55-252w"

-- 1. สร้าง ScreenGui หลัก
local screenGui = Instance.new("ScreenGui")
screenGui.Name = "DOEHubPaidGui"
screenGui.ResetOnSpawn = false
screenGui.IgnoreGuiInset = true
screenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
screenGui.Parent = PlayerGui

-- 2. ปุ่มเปิด-ปิดหน้าต่างที่มุมจอ (ซ่อนไว้ก่อนจนกว่าจะใส่คีย์ผ่าน)
local toggleButton = Instance.new("TextButton")
toggleButton.Name = "ToggleButton"
toggleButton.Size = UDim2.new(0, 130, 0, 42)
toggleButton.Position = UDim2.new(0, 20, 0, 20)
toggleButton.BackgroundColor3 = Color3.fromRGB(20, 20, 25)
toggleButton.Text = "💎 DOE HUB [PRO]"
toggleButton.TextColor3 = Color3.fromRGB(255, 215, 0)
toggleButton.TextSize = 14
toggleButton.Font = Enum.Font.GothamBold
toggleButton.Visible = false -- ซ่อนไว้ตอนยังไม่ใส่คีย์
toggleButton.Parent = screenGui

local toggleCorner = Instance.new("UICorner")
toggleCorner.CornerRadius = UDim.new(0, 10)
toggleCorner.Parent = toggleButton

local toggleStroke = Instance.new("UIStroke")
toggleStroke.Color = Color3.fromRGB(255, 180, 0)
toggleStroke.Thickness = 2
toggleStroke.Parent = toggleButton

-- ==================== 3. หน้าต่างใส่ KEY SYSTEM ====================
local keyGui = Instance.new("Frame")
keyGui.Name = "KeySystemFrame"
keyGui.Size = UDim2.new(0, 360, 0, 220)
keyGui.Position = UDim2.new(0.5, -180, 0.5, -110)
keyGui.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
keyGui.BorderSizePixel = 0
keyGui.Active = true
keyGui.Parent = screenGui

local keyCorner = Instance.new("UICorner")
keyCorner.CornerRadius = UDim.new(0, 16)
keyCorner.Parent = keyGui

local keyStroke = Instance.new("UIStroke")
keyStroke.Color = Color3.fromRGB(255, 215, 0)
keyStroke.Thickness = 2
keyStroke.Parent = keyGui

local keyTitle = Instance.new("TextLabel")
keyTitle.Size = UDim2.new(1, 0, 0, 50)
keyTitle.Position = UDim2.new(0, 0, 0, 10)
keyTitle.BackgroundTransparency = 1
keyTitle.Text = "🔐 DOE HUB - KEY SYSTEM"
keyTitle.TextColor3 = Color3.fromRGB(255, 255, 255)
keyTitle.TextSize = 18
keyTitle.Font = Enum.Font.GothamBold
keyTitle.Parent = keyGui

local keyDesc = Instance.new("TextLabel")
keyDesc.Size = UDim2.new(1, -40, 0, 30)
keyDesc.Position = UDim2.new(0, 20, 0, 60)
keyDesc.BackgroundTransparency = 1
keyDesc.Text = "กรุณากรอก Key เพื่อปลดล็อกการใช้งานสคริปต์"
keyDesc.TextColor3 = Color3.fromRGB(160, 160, 180)
keyDesc.TextSize = 13
keyDesc.Font = Enum.Font.GothamMedium
keyDesc.Parent = keyGui

local keyBox = Instance.new("TextBox")
keyBox.Size = UDim2.new(1, -40, 0, 42)
keyBox.Position = UDim2.new(0, 20, 0, 100)
keyBox.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
keyBox.PlaceholderText = "👉 ใส่ Key ที่นี่..."
keyBox.PlaceholderColor3 = Color3.fromRGB(100, 100, 120)
keyBox.Text = ""
keyBox.TextColor3 = Color3.fromRGB(255, 255, 255)
keyBox.TextSize = 14
keyBox.Font = Enum.Font.GothamMedium
keyBox.ClearTextOnFocus = false
keyBox.Parent = keyGui

local keyBoxCorner = Instance.new("UICorner")
keyBoxCorner.CornerRadius = UDim.new(0, 10)
keyBoxCorner.Parent = keyBox

local submitBtn = Instance.new("TextButton")
submitBtn.Size = UDim2.new(1, -40, 0, 40)
submitBtn.Position = UDim2.new(0, 20, 0, 155)
submitBtn.BackgroundColor3 = Color3.fromRGB(255, 180, 0)
submitBtn.Text = "VERIFY KEY"
submitBtn.TextColor3 = Color3.fromRGB(15, 15, 20)
submitBtn.TextSize = 14
submitBtn.Font = Enum.Font.GothamBold
submitBtn.Parent = keyGui

local submitCorner = Instance.new("UICorner")
submitCorner.CornerRadius = UDim.new(0, 10)
submitCorner.Parent = submitBtn

-- ==================== 4. หน้าต่างหลัก (Main Hub) ====================
local mainFrame = Instance.new("Frame")
mainFrame.Name = "MainFrame"
mainFrame.Size = UDim2.new(0, 340, 0, 480)
mainFrame.Position = UDim2.new(0.5, -170, 0.5, -240)
mainFrame.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
mainFrame.BorderSizePixel = 0
mainFrame.Visible = false -- ซ่อนไว้จนกว่าจะใส่คีย์ถูก
mainFrame.Active = true
mainFrame.Parent = screenGui

local uiCorner = Instance.new("UICorner")
uiCorner.CornerRadius = UDim.new(0, 14)
uiCorner.Parent = mainFrame

local uiStroke = Instance.new("UIStroke")
uiStroke.Color = Color3.fromRGB(255, 180, 0)
uiStroke.Thickness = 2
uiStroke.Parent = mainFrame

-- แถบหัวข้อค่าย (Top Bar / Header)
local topBar = Instance.new("Frame")
topBar.Size = UDim2.new(1, 0, 0, 45)
topBar.BackgroundTransparency = 1
topBar.Parent = mainFrame

local titleLabel = Instance.new("TextLabel")
titleLabel.Size = UDim2.new(1, -100, 1, 0)
titleLabel.Position = UDim2.new(0, 16, 0, 0)
titleLabel.BackgroundTransparency = 1
titleLabel.Text = "💎 DOE HUB <font color='#FFD700' size='12'>[Paid Version]</font>"
titleLabel.RichText = true
titleLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
titleLabel.TextSize = 16
titleLabel.Font = Enum.Font.GothamBold
titleLabel.TextXAlignment = Enum.TextXAlignment.Left
titleLabel.Parent = topBar

-- ปุ่มปิดหน้าต่าง (✕)
local closeButton = Instance.new("TextButton")
closeButton.Size = UDim2.new(0, 28, 0, 28)
closeButton.Position = UDim2.new(1, -36, 0.5, -14)
closeButton.BackgroundColor3 = Color3.fromRGB(235, 60, 60)
closeButton.Text = "✕"
closeButton.TextColor3 = Color3.fromRGB(255, 255, 255)
closeButton.TextSize = 13
closeButton.Font = Enum.Font.GothamBold
closeButton.Parent = topBar

local closeCorner = Instance.new("UICorner")
closeCorner.CornerRadius = UDim.new(0, 7)
closeCorner.Parent = closeButton

-- ปุ่มย่อหน้าต่าง (-)
local minimizeButton = Instance.new("TextButton")
minimizeButton.Size = UDim2.new(0, 28, 0, 28)
minimizeButton.Position = UDim2.new(1, -70, 0.5, -14)
minimizeButton.BackgroundColor3 = Color3.fromRGB(50, 50, 65)
minimizeButton.Text = "-"
minimizeButton.TextColor3 = Color3.fromRGB(220, 220, 230)
minimizeButton.TextSize = 16
minimizeButton.Font = Enum.Font.GothamBold
minimizeButton.Parent = topBar

local minCorner = Instance.new("UICorner")
minCorner.CornerRadius = UDim.new(0, 7)
minCorner.Parent = minimizeButton

-- ระบบย่อหน้าต่าง
local isMinimized = false
minimizeButton.MouseButton1Click:Connect(function()
	isMinimized = not isMinimized
	for _, child in ipairs(mainFrame:GetChildren()) do
		if child ~= topBar and child ~= uiCorner and child ~= uiStroke then
			child.Visible = not isMinimized
		end
	end
	mainFrame.Size = isMinimized and UDim2.new(0, 340, 0, 45) or UDim2.new(0, 340, 0, 480)
end)

closeButton.MouseButton1Click:Connect(function()
	mainFrame.Visible = false
end)

toggleButton.MouseButton1Click:Connect(function()
	mainFrame.Visible = not mainFrame.Visible
end)

-- ช่องค้นหาผู้เล่น
local searchBox = Instance.new("TextBox")
searchBox.Size = UDim2.new(1, -24, 0, 38)
searchBox.Position = UDim2.new(0, 12, 0, 52)
searchBox.BackgroundColor3 = Color3.fromRGB(22, 22, 30)
searchBox.PlaceholderText = "🔍 ค้นหาชื่อผู้เล่น..."
searchBox.PlaceholderColor3 = Color3.fromRGB(100, 100, 120)
searchBox.Text = ""
searchBox.TextColor3 = Color3.fromRGB(255, 255, 255)
searchBox.TextSize = 13
searchBox.Font = Enum.Font.GothamMedium
searchBox.ClearTextOnFocus = false
searchBox.Parent = mainFrame

local searchCorner = Instance.new("UICorner")
searchCorner.CornerRadius = UDim.new(0, 9)
searchCorner.Parent = searchBox

-- รายชื่อผู้เล่น (ScrollingFrame)
local scrollingFrame = Instance.new("ScrollingFrame")
scrollingFrame.Size = UDim2.new(1, -24, 1, -150)
scrollingFrame.Position = UDim2.new(0, 12, 0, 100)
scrollingFrame.BackgroundTransparency = 1
scrollingFrame.BorderSizePixel = 0
scrollingFrame.CanvasSize = UDim2.new(0, 0, 0, 0)
scrollingFrame.ScrollBarThickness = 4
scrollingFrame.ScrollBarImageColor3 = Color3.fromRGB(255, 180, 0)
scrollingFrame.Parent = mainFrame

local uiLayout = Instance.new("UIListLayout")
uiLayout.SortOrder = Enum.SortOrder.LayoutOrder
uiLayout.Padding = UDim.new(0, 8)
uiLayout.Parent = scrollingFrame

-- แถบหยุดเดินตาม
local controlBar = Instance.new("Frame")
controlBar.Size = UDim2.new(0, 240, 0, 48)
controlBar.Position = UDim2.new(0.5, -120, 1, -65)
controlBar.BackgroundColor3 = Color3.fromRGB(20, 20, 28)
controlBar.Visible = false
controlBar.Parent = screenGui

local controlCorner = Instance.new("UICorner")
controlCorner.CornerRadius = UDim.new(0, 24)
controlCorner.Parent = controlBar

local controlStroke = Instance.new("UIStroke")
controlStroke.Color = Color3.fromRGB(255, 75, 75)
controlStroke.Thickness = 2
controlStroke.Parent = controlBar

local stopButton = Instance.new("TextButton")
stopButton.Size = UDim2.new(1, 0, 1, 0)
stopButton.BackgroundTransparency = 1
stopButton.Text = "🛑 หยุดตาม & กลับจุดเดิม"
stopButton.TextColor3 = Color3.fromRGB(255, 100, 100)
stopButton.TextSize = 13
stopButton.Font = Enum.Font.GothamBold
stopButton.Parent = controlBar

-- Popup ยืนยันการตาม
local confirmOverlay = Instance.new("Frame")
confirmOverlay.Size = UDim2.new(1, 0, 1, 0)
confirmOverlay.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
confirmOverlay.BackgroundTransparency = 0.6
confirmOverlay.Visible = false
confirmOverlay.ZIndex = 10
confirmOverlay.Parent = mainFrame

local confirmBox = Instance.new("Frame")
confirmBox.Size = UDim2.new(0, 270, 0, 145)
confirmBox.Position = UDim2.new(0.5, -135, 0.5, -72)
confirmBox.BackgroundColor3 = Color3.fromRGB(22, 22, 30)
confirmBox.BorderSizePixel = 0
confirmBox.ZIndex = 11
confirmBox.Parent = confirmOverlay

local boxCorner = Instance.new("UICorner")
boxCorner.CornerRadius = UDim.new(0, 12)
boxCorner.Parent = confirmBox

local boxStroke = Instance.new("UIStroke")
boxStroke.Color = Color3.fromRGB(255, 180, 0)
boxStroke.Thickness = 1.5
boxStroke.ZIndex = 11
boxStroke.Parent = confirmBox

local confirmText = Instance.new("TextLabel")
confirmText.Size = UDim2.new(1, -20, 0, 60)
confirmText.Position = UDim2.new(0, 10, 0, 12)
confirmText.BackgroundTransparency = 1
confirmText.Text = "ต้องการเดินตามผู้เล่นนี้ใช่หรือไม่?"
confirmText.TextColor3 = Color3.fromRGB(255, 255, 255)
confirmText.TextSize = 14
confirmText.Font = Enum.Font.GothamMedium
confirmText.TextWrapped = true
confirmText.ZIndex = 12
confirmText.Parent = confirmBox

local yesButton = Instance.new("TextButton")
yesButton.Size = UDim2.new(0, 115, 0, 36)
yesButton.Position = UDim2.new(0, 15, 1, -50)
yesButton.BackgroundColor3 = Color3.fromRGB(255, 180, 0)
yesButton.Text = "YES"
yesButton.TextColor3 = Color3.fromRGB(15, 15, 20)
yesButton.Font = Enum.Font.GothamBold
yesButton.TextSize = 14
yesButton.ZIndex = 12
yesButton.Parent = confirmBox

local yesCorner = Instance.new("UICorner")
yesCorner.CornerRadius = UDim.new(0, 8)
yesCorner.Parent = yesButton

local noButton = Instance.new("TextButton")
noButton.Size = UDim2.new(0, 115, 0, 36)
noButton.Position = UDim2.new(1, -130, 1, -50)
noButton.BackgroundColor3 = Color3.fromRGB(45, 45, 60)
noButton.Text = "NO"
noButton.TextColor3 = Color3.fromRGB(255, 255, 255)
noButton.Font = Enum.Font.GothamBold
noButton.TextSize = 14
noButton.ZIndex = 12
noButton.Parent = confirmBox

local noCorner = Instance.new("UICorner")
noCorner.CornerRadius = UDim.new(0, 8)
noCorner.Parent = noButton

-- ฟังก์ชันตรวจสอบ Key
submitBtn.MouseButton1Click:Connect(function()
	if keyBox.Text == CORRECT_KEY then
		keyGui.Visible = false
		mainFrame.Visible = true
		toggleButton.Visible = true
	else
		keyBox.Text = ""
		keyBox.PlaceholderText = "❌ Key ไม่ถูกต้อง ลองใหม่อีกครั้ง!"
	end
end)

-- ตัวแปรระบบทำงาน
local selectedTargetPlayer = nil
local followingConnection = nil
local originalPosition = nil

-- ฟังก์ชันอัปเดตรายชื่อ
local function updatePlayerList()
	for _, child in ipairs(scrollingFrame:GetChildren()) do
		if child:IsA("TextButton") then
			child:Destroy()
		end
	end

	local searchText = string.lower(searchBox.Text)
	local count = 0

	for _, player in ipairs(Players:GetPlayers()) do
		if player ~= LocalPlayer then
			local displayName = string.lower(player.DisplayName)
			local username = string.lower(player.Name)
			
			if searchText == "" or string.find(displayName, searchText) or string.find(username, searchText) then
				count = count + 1
				
				local playerButton = Instance.new("TextButton")
				playerButton.Size = UDim2.new(1, 0, 0, 52)
				playerButton.BackgroundColor3 = Color3.fromRGB(22, 22, 30)
				playerButton.AutoButtonColor = false
				playerButton.Text = ""
				playerButton.Parent = scrollingFrame

				local btnCorner = Instance.new("UICorner")
				btnCorner.CornerRadius = UDim.new(0, 10)
				btnCorner.Parent = playerButton

				local iconImage = Instance.new("ImageLabel")
				iconImage.Size = UDim2.new(0, 36, 0, 36)
				iconImage.Position = UDim2.new(0, 8, 0.5, -18)
				iconImage.BackgroundTransparency = 1
				iconImage.Parent = playerButton

				local imgCorner = Instance.new("UICorner")
				imgCorner.CornerRadius = UDim.new(1, 0)
				imgCorner.Parent = iconImage

				task.spawn(function()
					local success, content = pcall(function()
						return Players:GetUserThumbnailAsync(player.UserId, Enum.ThumbnailType.HeadShot, Enum.ThumbnailSize.Size150x150)
					end)
					if success and content then
						iconImage.Image = content
					end
				end)

				local nameLabel = Instance.new("TextLabel")
				nameLabel.Size = UDim2.new(1, -56, 1, 0)
				nameLabel.Position = UDim2.new(0, 52, 0, 0)
				nameLabel.BackgroundTransparency = 1
				nameLabel.Text = player.DisplayName .. " (@" .. player.Name .. ")"
				nameLabel.TextColor3 = Color3.fromRGB(230, 230, 240)
				nameLabel.TextSize = 13
				nameLabel.Font = Enum.Font.GothamMedium
				nameLabel.TextXAlignment = Enum.TextXAlignment.Left
				nameLabel.Parent = playerButton

				playerButton.MouseButton1Click:Connect(function()
					selectedTargetPlayer = player
					confirmText.Text = "ต้องการเดินตาม " .. player.DisplayName .. " ใช่หรือไม่?"
					confirmOverlay.Visible = true
				end)
			end
		end
	end

	scrollingFrame.CanvasSize = UDim2.new(0, 0, 0, count * 60)
end

local function stopFollowing()
	if followingConnection then
		followingConnection:Disconnect()
		followingConnection = nil
	end
	
	if originalPosition and LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart") then
		LocalPlayer.Character.HumanoidRootPart.CFrame = originalPosition
	end
	
	controlBar.Visible = false
	selectedTargetPlayer = nil
end

yesButton.MouseButton1Click:Connect(function()
	if selectedTargetPlayer then
		local character = LocalPlayer.Character
		if character and character:FindFirstChild("HumanoidRootPart") then
			originalPosition = character.HumanoidRootPart.CFrame
			
			if followingConnection then
				followingConnection:Disconnect()
			end
			
			followingConnection = RunService.RenderStepped:Connect(function()
				if selectedTargetPlayer.Character and selectedTargetPlayer.Character:FindFirstChild("HumanoidRootPart") then
					local targetRoot = selectedTargetPlayer.Character.HumanoidRootPart
					local myRoot = character:FindFirstChild("HumanoidRootPart")
					if myRoot then
						myRoot.CFrame = targetRoot.CFrame * CFrame.new(0, 3, 4)
					end
				else
					stopFollowing()
				end
			end)
			
			controlBar.Visible = true
		end
	end
	confirmOverlay.Visible = false
	mainFrame.Visible = false
end)

noButton.MouseButton1Click:Connect(function()
	confirmOverlay.Visible = false
	selectedTargetPlayer = nil
end)

stopButton.MouseButton1Click:Connect(function()
	stopFollowing()
end)

searchBox:GetPropertyChangedSignal("Text"):Connect(updatePlayerList)
Players.PlayerAdded:Connect(updatePlayerList)
Players.PlayerRemoving:Connect(updatePlayerList)
updatePlayerList()

-- ระบบลากหน้าต่างทั้ง Key System และ Main Hub
local function makeDraggable(frame)
	local dragging, dragStart, startPos
	frame.InputBegan:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
			dragging = true
			dragStart = input.Position
			startPos = frame.Position
			input.Changed:Connect(function()
				if input.UserInputState == Enum.UserInputState.End then
					dragging = false
				end
			end)
		end
	end)
	UserInputService.InputChanged:Connect(function(input)
		if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
			local delta = input.Position - dragStart
			frame.Position = UDim2.new(
				startPos.X.Scale, 
				startPos.X.Offset + delta.X, 
				startPos.Y.Scale, 
				startPos.Y.Offset + delta.Y
			)
		end
	end)
end

makeDraggable(keyGui)
makeDraggable(mainFrame)
